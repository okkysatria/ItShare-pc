"""
core/smb_server.py - Detached SMB service manager for ItShare.
Features:
- Run in dedicated child process (daemon=True) for isolation and crash resilience
- Custom port support (default 4455)
- NTLM authentication with random credentials
- Read-only vs Read-Write enforcement
- Port conflict detection (Errno 10048 / 98)
- Safe start(), stop(), and is_running() interface
- Queue-based event and status monitoring
"""
import os
import sys
import time
import socket
import json
import logging
import binascii
import multiprocessing
import queue
import threading
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from core.session import ShareSession

logger = logging.getLogger(__name__)

def _run_impacket_server(
    listen_ip: str,
    port: int,
    share_name: str,
    folder_path: str,
    username: str,
    password: str,
    read_only: bool,
    status_queue: multiprocessing.Queue,
    event_queue: multiprocessing.Queue
):
    """
    Child process entrypoint: initializes and starts impacket SimpleSMBServer.
    Reports startup success or port collision back via status_queue.
    """

    logging.basicConfig(level=logging.INFO)
    impacket_logger = logging.getLogger("impacket")
    impacket_logger.setLevel(logging.INFO)

    from impacket.smbserver import SimpleSMBServer
    from impacket.ntlm import compute_lmhash, compute_nthash

    server = None
    try:

        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            test_sock.bind((listen_ip, port))
        except OSError as e:

            status_queue.put({
                "status": "error",
                "error_type": "PORT_IN_USE",
                "message": f"Port {port} sudah digunakan oleh aplikasi lain ({e}). Silakan coba port lain."
            })
            return
        finally:
            test_sock.close()

        server = SimpleSMBServer(listenAddress=listen_ip, listenPort=port)

        ro_flag = "yes" if read_only else "no"
        server.addShare(
            shareName=share_name,
            sharePath=folder_path,
            shareComment="ItShare",
            shareType="0",
            readOnly=ro_flag
        )

        lm_hash = binascii.hexlify(compute_lmhash(password)).decode()
        nt_hash = binascii.hexlify(compute_nthash(password)).decode()
        server.addCredential(username, 0, lm_hash, nt_hash)

        server.setSMB2Support(True)
        server.setNTLMSupport(True)
        server.setKerberosSupport(False)

    except Exception as e:
        status_queue.put({
            "status": "error",
            "error_type": "INIT_FAILED",
            "message": str(e)
        })
        return

    serve_errors = []
    def serve():
        try:
            server.start()
        except Exception as e:
            serve_errors.append(e)
    serve_thread = threading.Thread(target=serve, name="itshare-smb", daemon=True)
    serve_thread.start()
    deadline = time.monotonic() + 3.0
    ready = False
    while time.monotonic() < deadline:
        if serve_errors or not serve_thread.is_alive():
            status_queue.put({"status": "error", "error_type": "START_FAILED",
                "message": str(serve_errors[0]) if serve_errors else "Loop server SMB berhenti saat startup."})
            return
        try:
            probe_ip = "127.0.0.1" if listen_ip in ("0.0.0.0", "") else listen_ip
            with socket.create_connection((probe_ip, port), timeout=0.2):
                ready = True
                break
        except OSError:
            time.sleep(0.05)
    if not ready:
        status_queue.put({"status": "error", "error_type": "START_TIMEOUT",
            "message": "Server SMB tidak mulai menerima koneksi dalam batas waktu."})
        return
    status_queue.put({"status": "started", "ip": listen_ip, "port": port})
    serve_thread.join()

_ACTIVE_SHARE_FILE = Path.home() / ".itshare" / "active_share.json"
_STOP_REQUEST_FILE = _ACTIVE_SHARE_FILE.with_suffix(".stop")
_TRANSFER_HISTORY_FILE = Path.home() / ".itshare" / "transfer_history.jsonl"
_TRANSFER_HISTORY_LOCK = threading.Lock()

def _append_transfer_event(direction: str, file_path: str, byte_count: int, client_ip: str, share_name: str) -> None:
    """Persist SMB file I/O events from Android without recording credentials."""
    event = {
        "direction": direction,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "client": client_ip,
        "share": share_name,
        "file_name": Path(file_path).name,
        "size_bytes": max(0, int(byte_count)),
    }
    try:
        _TRANSFER_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _TRANSFER_HISTORY_LOCK, _TRANSFER_HISTORY_FILE.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("Could not persist SMB transfer activity")

def _install_transfer_audit(server) -> None:
    """Observe completed SMB2 file reads/writes and record one event per file handle."""
    from impacket import smb3structs as smb2

    smb_server = server.getServer()
    original_create = smb_server.hookSmb2Command(smb2.SMB2_CREATE, lambda *args: None)
    original_read = smb_server.hookSmb2Command(smb2.SMB2_READ, lambda *args: None)
    original_write = smb_server.hookSmb2Command(smb2.SMB2_WRITE, lambda *args: None)
    original_close = smb_server.hookSmb2Command(smb2.SMB2_CLOSE, lambda *args: None)

    def create(conn_id, smb_impl, packet):
        request = smb2.SMB2Create(packet["Data"])
        result = original_create(conn_id, smb_impl, packet)
        try:
            if result[2] != 0:
                return result
            data = smb_impl.getConnectionData(conn_id)
            response = data.get("LastRequest", {}).get("SMB2_CREATE")
            if response is None:
                return result
            file_id = response["FileID"].getData()
            opened = data.get("OpenedFiles", {}).get(file_id)
            if not opened or not os.path.isfile(opened.get("FileName", "")):
                return result
            access = int(request["DesiredAccess"])
            is_write = bool(access & (0x2 | 0x40000000 | 0x10000000))
            is_read = bool(access & (0x1 | 0x80000000 | 0x10000000))
            opened["ItShareAudit"] = {
                "direction": "upload" if is_write else "download" if is_read else "",
                "path": opened["FileName"],
                "size": os.path.getsize(opened["FileName"]),
                "bytes": 0,
                "started": time.monotonic(),
                "client": str(data.get("ClientIP") or ""),
                "share": str(data.get("ConnectedShares", {}).get(packet["TreeID"], {}).get("shareName") or ""),
            }
            smb_impl.setConnectionData(conn_id, data)
        except Exception:
            logger.debug("Unable to initialize SMB transfer audit", exc_info=True)
        return result

    def get_audit(data, packet, request_type):
        try:
            request = request_type(packet["Data"])
            file_id = request["FileID"].getData()
            if file_id == b"\xff" * 16:
                response = data.get("LastRequest", {}).get("SMB2_CREATE")
                if response is not None:
                    file_id = response["FileID"].getData()
            opened = data.get("OpenedFiles", {}).get(file_id)
            return opened.get("ItShareAudit") if opened else None
        except Exception:
            return None

    def read(conn_id, smb_impl, packet):
        data = smb_impl.getConnectionData(conn_id)
        audit = get_audit(data, packet, smb2.SMB2Read)
        result = original_read(conn_id, smb_impl, packet)
        try:
            if audit is not None and result[2] == 0 and result[0]:
                audit["bytes"] += int(result[0][0]["DataLength"])
                smb_impl.setConnectionData(conn_id, data)
        except Exception:
            logger.debug("Unable to update SMB read audit", exc_info=True)
        return result

    def write(conn_id, smb_impl, packet):
        data = smb_impl.getConnectionData(conn_id)
        audit = get_audit(data, packet, smb2.SMB2Write)
        result = original_write(conn_id, smb_impl, packet)
        try:
            if audit is not None and result[2] == 0 and result[0]:
                audit["bytes"] += int(result[0][0]["Count"])
                smb_impl.setConnectionData(conn_id, data)
        except Exception:
            logger.debug("Unable to update SMB write audit", exc_info=True)
        return result

    def close(conn_id, smb_impl, packet):
        data = smb_impl.getConnectionData(conn_id)
        try:
            request = smb2.SMB2Close(packet["Data"])
            file_id = request["FileID"].getData()
            if file_id == b"\xff" * 16:
                last_create = data.get("LastRequest", {}).get("SMB2_CREATE")
                if last_create is not None:
                    file_id = last_create["FileID"].getData()
            audit = data.get("OpenedFiles", {}).get(file_id, {}).get("ItShareAudit")
        except Exception:
            audit = None
        result = original_close(conn_id, smb_impl, packet)
        try:
            is_complete_read = audit and audit["direction"] == "download" and audit["bytes"] >= audit["size"]
            is_upload = audit and audit["direction"] == "upload" and audit["bytes"] > 0
            if audit and result[2] == 0 and (is_upload or is_complete_read):
                _append_transfer_event(
                    audit["direction"], audit["path"], audit["bytes"], audit["client"], audit["share"]
                )
        except Exception:
            logger.debug("Unable to finalize SMB transfer audit", exc_info=True)
        return result

    smb_server.hookSmb2Command(smb2.SMB2_CREATE, create)
    smb_server.hookSmb2Command(smb2.SMB2_READ, read)
    smb_server.hookSmb2Command(smb2.SMB2_WRITE, write)
    smb_server.hookSmb2Command(smb2.SMB2_CLOSE, close)

def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    os.replace(temp_path, path)

def run_detached_service(state_path: str) -> int:
    """Standalone SMB process. It is intentionally independent of the UI."""
    state_file = Path(state_path)
    stop_file = state_file.with_suffix(".stop")
    try:
        with state_file.open("r", encoding="utf-8") as stream:
            state = json.load(stream)
        token = str(state["token"])
        pid = os.getpid()
        state.update(pid=pid, status="starting", error="")
        _write_json_atomic(state_file, state)

        server = None
        try:
            from impacket.smbserver import SimpleSMBServer
            from impacket.ntlm import compute_lmhash, compute_nthash

            listen_ip = state.get("host_ip") or "0.0.0.0"
            port = int(state["port"])
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((listen_ip, port))
            except OSError as exc:
                raise RuntimeError(f"Port {port} sudah digunakan oleh aplikasi lain ({exc}).")
            finally:
                probe.close()

            server = SimpleSMBServer(listenAddress=listen_ip, listenPort=port)
            shares = state.get("shares") or [state]
            credentials = set()
            for share in shares:
                server.addShare(
                    shareName=share["share_name"],
                    sharePath=share["folder_path"],
                    shareComment="ItShare",
                    shareType="0",
                    readOnly="yes" if share["read_only"] else "no",
                )
                credentials.add((str(share["username"]), str(share["password"])))
            for username, password in credentials:
                lm_hash = binascii.hexlify(compute_lmhash(password)).decode()
                nt_hash = binascii.hexlify(compute_nthash(password)).decode()

                server.addCredential(username, 0, lm_hash, nt_hash)
            server.setSMB2Support(True)

            server.setNTLMSupport(True)
            server.setKerberosSupport(False)
            _install_transfer_audit(server)

            errors = []
            def serve():
                try:
                    server.start()
                except Exception as exc:
                    errors.append(str(exc))

            serve_thread = threading.Thread(target=serve, name="itshare-smb", daemon=True)
            serve_thread.start()
            deadline = time.monotonic() + 5.0
            ready = False
            while time.monotonic() < deadline and serve_thread.is_alive():
                try:
                    probe_ip = "127.0.0.1" if listen_ip in ("0.0.0.0", "") else listen_ip
                    with socket.create_connection((probe_ip, port), timeout=0.2):
                        owns_listener = True
                        if os.name == "nt":
                            netstat = subprocess.run(
                                ["netstat", "-ano", "-p", "tcp"],
                                capture_output=True, text=True, errors="replace", timeout=2, check=False,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            )
                            owns_listener = any(
                                len(fields := line.split()) >= 5
                                and fields[0].upper() == "TCP"
                                and fields[1].rsplit(":", 1)[-1] == str(port)
                                and fields[3].upper() == "LISTENING"
                                and fields[4] == str(pid)
                                for line in netstat.stdout.splitlines()
                            )
                        if owns_listener:
                            ready = True
                            break
                        time.sleep(0.05)
                except OSError:
                    time.sleep(0.05)
            if not ready:
                raise RuntimeError(errors[0] if errors else "Server SMB tidak memiliki listener pada port yang dipilih; mungkin masih dipakai service ItShare lama.")

            state.update(status="running", pid=pid, error="")
            _write_json_atomic(state_file, state)
            while True:
                if int(state.get("timeout_minutes", 0)) > 0:
                    expires_at = float(state["created_at"]) + int(state["timeout_minutes"]) * 60

                    if time.time() >= expires_at + 3.0:
                        break
                try:
                    with stop_file.open("r", encoding="utf-8") as stream:
                        stop_request = json.load(stream)
                    if stop_request.get("token") == token:
                        break
                except (OSError, ValueError):
                    pass
                if not serve_thread.is_alive():
                    raise RuntimeError(errors[0] if errors else "Proses server SMB berhenti.")
                time.sleep(0.25)
        except Exception as exc:
            state.update(status="error", pid=pid, error=str(exc))
            _write_json_atomic(state_file, state)
            time.sleep(0.5)
            return 1
        return 0
    except Exception:
        logger.exception("Detached SMB service failed")
        return 1
    finally:
        try:
            with state_file.open("r", encoding="utf-8") as stream:
                latest = json.load(stream)
            if latest.get("token") == locals().get("token") and latest.get("status") != "error":
                state_file.unlink(missing_ok=True)
                stop_file.unlink(missing_ok=True)
        except (OSError, ValueError):
            pass

class SMBServerManager:
    """Controls a detached SMB service that survives the desktop UI process."""
    def __init__(self):
        self._service_process: Optional[subprocess.Popen] = None
        self._active_session: Optional[ShareSession] = None
        self._state_path = _ACTIVE_SHARE_FILE
        self._stop_path = _STOP_REQUEST_FILE
        self._restore_existing_service()

    def _list_listener_pids(self, port: int) -> set[int]:
        """Return PIDs listening on a TCP port (used to detect orphan SMB workers)."""
        try:
            command = ["netstat", "-ano", "-p", "tcp"] if os.name == "nt" else ["netstat", "-ltnp"]
            result = subprocess.run(
                command, capture_output=True, text=True, errors="replace", timeout=3,
                check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            )
            listeners = set()
            for line in result.stdout.splitlines():
                fields = line.split()
                if len(fields) < 5 or fields[0].upper() != "TCP":
                    continue
                if fields[1].rsplit(":", 1)[-1] != str(int(port)):
                    continue
                state_index, pid_index = (3, 4) if os.name == "nt" else (5, 6)
                if len(fields) > pid_index and fields[state_index].upper() in {"LISTENING", "LISTEN"}:
                    try:
                        listeners.add(int(fields[pid_index]))
                    except ValueError:
                        pass
            return listeners
        except (OSError, subprocess.SubprocessError, ValueError):
            logger.debug("Unable to inspect SMB listener PID", exc_info=True)
            return set()

    def _stop_orphaned_service_listeners(self, port: int) -> None:
        """Stop only stale ItShare workers tied to this app's SMB state file."""
        if os.name != "nt":
            return
        marker = str(self._state_path).replace("'", "''")
        for pid in self._list_listener_pids(port):
            if pid == os.getpid():
                continue
            script = (
                f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; "
                f"if ($p -and $p.CommandLine -like '*--itshare-smb-service*' "
                f"-and $p.CommandLine -like '*{marker}*') "
                f"{{ Stop-Process -Id {pid} -Force; exit 0 }}; exit 3"
            )
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True, text=True, errors="replace", timeout=4, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0:
                    logger.warning("Stopped stale ItShare SMB listener PID %s on port %s", pid, port)
                    deadline = time.monotonic() + 2.0
                    while time.monotonic() < deadline and self._pid_is_alive(pid):
                        time.sleep(0.05)
            except (OSError, subprocess.SubprocessError):
                logger.exception("Could not stop stale ItShare SMB listener PID %s", pid)

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel32.OpenProcess.restype = wintypes.HANDLE
                kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel32.WaitForSingleObject.restype = wintypes.DWORD
                kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
                process = kernel32.OpenProcess(0x00100000 | 0x1000, False, pid)
                if not process:
                    return False
                try:
                    return kernel32.WaitForSingleObject(process, 0) == 0x00000102
                finally:
                    kernel32.CloseHandle(process)
            except (OSError, AttributeError):
                logger.exception("Could not inspect SMB service process")
                return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _read_state(self) -> Optional[dict]:
        try:
            with self._state_path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def _session_from_state(self, state: dict) -> ShareSession:
        return ShareSession(
            folder_path=str(state["folder_path"]),
            username=str(state["username"]),
            password=str(state["password"]),
            port=int(state["port"]),
            read_only=bool(state["read_only"]),
            timeout_minutes=int(state.get("timeout_minutes", 0)),
            created_at=float(state.get("created_at", time.time())),
            status="running",
            share_name=str(state["share_name"]),
            host_ip=str(state.get("host_ip") or "127.0.0.1"),
        )

    def _sessions_from_state(self, state: dict) -> List[ShareSession]:
        shares = state.get("shares") or [state]
        sessions = []
        for share in shares:
            merged = dict(state)
            merged.update(share)
            sessions.append(self._session_from_state(merged))
        return sessions

    def _restore_existing_service(self) -> None:
        state = self._read_state()
        if not state or state.get("status") not in ("starting", "running"):
            return
        try:
            pid = int(state.get("pid", 0))
            if not self._pid_is_alive(pid):
                self._state_path.unlink(missing_ok=True)
                self._stop_path.unlink(missing_ok=True)
                return
            sessions = self._sessions_from_state(state)
            self._active_session = sessions[0] if sessions else None
        except (KeyError, TypeError, ValueError, OSError):
            logger.exception("Could not restore active SMB session")

    def start(self, session: ShareSession, sessions: Optional[List[ShareSession]] = None) -> Tuple[bool, str]:
        sessions = list(sessions or [session])
        if not sessions:
            return False, "Tambahkan setidaknya satu folder untuk dibagikan."
        timed_sessions = [item for item in sessions if item.timeout_minutes > 0]
        session = min(timed_sessions, key=lambda item: item.expires_at) if timed_sessions else sessions[0]
        if self.is_running():
            self.stop()

        self._stop_orphaned_service_listeners(int(session.port))

        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop_path.unlink(missing_ok=True)
        token = uuid.uuid4().hex
        state = {
            "token": token,
            "pid": 0,
            "status": "starting",
            "error": "",
            "folder_path": session.folder_path,
            "username": session.username,
            "password": session.password,
            "port": int(session.port),
            "read_only": bool(session.read_only),
            "timeout_minutes": int(session.timeout_minutes),
            "created_at": float(session.created_at),
            "share_name": session.share_name,
            "host_ip": session.host_ip or "0.0.0.0",
            "shares": [
                {
                    "folder_path": item.folder_path,
                    "username": item.username,
                    "password": item.password,
                    "port": int(item.port),
                    "read_only": bool(item.read_only),
                    "timeout_minutes": int(item.timeout_minutes),
                    "created_at": float(item.created_at),
                    "share_name": item.share_name,
                    "host_ip": item.host_ip or session.host_ip or "0.0.0.0",
                }
                for item in sessions
            ],
        }
        _write_json_atomic(self._state_path, state)

        if getattr(sys, "frozen", False):
            command = [sys.executable, "--itshare-smb-service", str(self._state_path)]
            working_dir = str(Path(sys.executable).resolve().parent)
        else:
            entrypoint = Path(__file__).resolve().parent.parent / "main.py"
            command = [sys.executable, str(entrypoint), "--itshare-smb-service", str(self._state_path)]
            working_dir = str(entrypoint.parent)

        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            self._service_process = subprocess.Popen(
                command,
                cwd=working_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creation_flags,
            )
        except Exception as exc:
            self._state_path.unlink(missing_ok=True)
            session.status = "error"
            return False, f"Tidak bisa menjalankan layanan SMB: {exc}"

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            latest = self._read_state()
            if latest and latest.get("token") == token:
                if latest.get("status") == "running":
                    for item in sessions:
                        item.status = "running"
                    self._active_session = session
                    return True, "Server SMB berjalan terpisah dan tetap aktif saat jendela ItShare ditutup."
                if latest.get("status") == "error":
                    message = str(latest.get("error") or "Gagal memulai server SMB.")
                    self._service_process = None
                    self._state_path.unlink(missing_ok=True)
                    session.status = "error"
                    return False, message
            if self._service_process.poll() is not None:
                break
            time.sleep(0.1)

        self.stop()
        session.status = "error"
        return False, "Layanan SMB tidak memberi konfirmasi siap dalam batas waktu."

    def stop(self) -> None:
        state = self._read_state()
        port = int(state.get("port", 0)) if state else int(getattr(self._active_session, "port", 0) or 0)
        if state and state.get("token") and self.is_running():
            try:
                _write_json_atomic(self._stop_path, {"token": state["token"]})
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline:
                    latest = self._read_state()
                    pid = int((latest or state).get("pid", 0))
                    if not self._pid_is_alive(pid):
                        break
                    time.sleep(0.1)
            except (OSError, TypeError, ValueError):
                logger.exception("Failed to request SMB service shutdown")

        if self._service_process is not None:
            try:
                self._service_process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
            self._service_process = None
        if port:
            self._stop_orphaned_service_listeners(port)
        if self._active_session:
            self._active_session.status = "stopped"
        self._active_session = None

    def is_running(self) -> bool:
        state = self._read_state()
        if not state or state.get("status") not in ("starting", "running"):
            return False
        try:
            return self._pid_is_alive(int(state.get("pid", 0)))
        except (TypeError, ValueError):
            return False

    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Return remote IPs with established TCP connections to this SMB service.

        This reports network peers, not authenticated SMB identities: Impacket's
        SimpleSMBServer does not expose a stable public client-session API.
        """
        state = self._read_state()
        if not state or not self.is_running():
            return []
        try:
            port = int(state["port"])
            service_pid = int(state.get("pid", 0))
            command = ["netstat", "-ano", "-p", "tcp"] if os.name == "nt" else ["netstat", "-tn"]
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            result = subprocess.run(
                command, capture_output=True, text=True, errors="replace",
                timeout=2, check=False, creationflags=creation_flags,
            )
            if result.returncode != 0:
                return []
        except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            logger.debug("Unable to read established SMB TCP connections", exc_info=True)
            return []

        peers: Dict[str, int] = {}
        for line in result.stdout.splitlines():
            columns = line.split()
            upper = [column.upper() for column in columns]
            try:
                state_index = upper.index("ESTABLISHED")
            except ValueError:
                continue
            if state_index < 2:
                continue
            local_endpoint, remote_endpoint = columns[state_index - 2:state_index]
            try:
                local_port = int(local_endpoint.rsplit(":", 1)[1])
            except (IndexError, ValueError):
                continue
            if local_port != port:
                continue

            if os.name == "nt":
                try:
                    if int(columns[state_index + 1]) != service_pid:
                        continue
                except (IndexError, ValueError):
                    continue
            address = remote_endpoint.rsplit(":", 1)[0].strip("[]")
            if address:
                peers[address] = peers.get(address, 0) + 1
        return [{"address": address, "connections": peers[address]} for address in sorted(peers)]

    @property
    def active_session(self) -> Optional[ShareSession]:
        if self._active_session is None and self.is_running():
            state = self._read_state()
            if state:
                try:
                    self._active_session = self._session_from_state(state)
                except (KeyError, TypeError, ValueError):
                    logger.exception("Could not load running SMB session")
        return self._active_session

    @property
    def active_sessions(self) -> List[ShareSession]:
        if not self.is_running():
            return []
        state = self._read_state()
        if not state:
            return []
        try:
            sessions = self._sessions_from_state(state)
            self._active_session = sessions[0] if sessions else None
            return sessions
        except (KeyError, TypeError, ValueError):
            logger.exception("Could not load running SMB shares")
            return []
