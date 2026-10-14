"""
tests/test_smb_integration.py - Integration and port tests for SMBServerManager.
"""
import time
import socket
import pytest
from core.session import ShareSession
from core.smb_server import SMBServerManager
from core.credentials import generate_username, generate_password

def test_smb_server_lifecycle(tmp_path):
    share_dir = tmp_path / "shared"
    share_dir.mkdir()
    (share_dir / "test.txt").write_text("Hello SMB", encoding="utf-8")

    session = ShareSession(
        folder_path=str(share_dir),
        username=generate_username(),
        password=generate_password(),
        port=14455,
        read_only=True,
        host_ip="127.0.0.1"
    )

    manager = SMBServerManager()
    success, msg = manager.start(session)
    assert success is True, f"Failed to start: {msg}"
    assert manager.is_running() is True
    assert session.status == "running"

    time.sleep(1)
    manager.stop()
    assert manager.is_running() is False
    assert session.status == "stopped"

def test_smb_port_conflict(tmp_path):

    conflict_port = 14456
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", conflict_port))
    sock.listen(1)

    try:
        session = ShareSession(
            folder_path=str(tmp_path),
            username=generate_username(),
            password=generate_password(),
            port=conflict_port,
            host_ip="127.0.0.1"
        )
        manager = SMBServerManager()
        success, msg = manager.start(session)
        assert success is False
        assert "sudah digunakan" in msg or "PORT_IN_USE" in msg or "Gagal" in msg
        assert manager.is_running() is False
    finally:
        sock.close()
