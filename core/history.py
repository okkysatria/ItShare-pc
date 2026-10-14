"""
core/history.py - Persistent share folder history, recent settings, and backup/import logic.
Config file location: ~/.itshare/config.json
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".itshare" / "config.json"
TRANSFER_HISTORY_PATH = Path.home() / ".itshare" / "transfer_history.jsonl"

@dataclass
class ImportResult:
    success: bool
    imported_count: int = 0
    message: str = ""
    error: Optional[str] = None

class HistoryManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: Dict[str, Any] = {
            "recent_folders": [],
            "folder_aliases": {},
            "connection_history": [],
            "settings": {
                "default_port": 4455,
                "default_read_only": True,
                "default_timeout_minutes": 0,
                "startup_page": 0,
                "folders_per_page": 8,
                "theme": "system",
                "language": "en",
                "show_folder_paths": True,
                "hide_qr_by_default": False,
                "confirm_before_stop": True,
                "keep_share_after_exit": True,
            }
        }
        self.load()

    def load(self) -> None:
        """Load configuration from config_path if it exists."""
        if not self.config_path.exists():
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data["recent_folders"] = loaded.get("recent_folders", [])
                    aliases = loaded.get("folder_aliases", {})
                    self._data["folder_aliases"] = aliases if isinstance(aliases, dict) else {}
                    connections = loaded.get("connection_history", [])
                    self._data["connection_history"] = connections if isinstance(connections, list) else []
                    if "settings" in loaded and isinstance(loaded["settings"], dict):
                        self._data["settings"].update(loaded["settings"])
        except Exception as e:
            logger.warning(f"Failed to load history config: {e}")

    def save(self) -> None:
        """Save configuration to disk safely."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history config: {e}")

    def add_folder(self, folder_path: str, max_items: int = 200) -> None:
        """
        Add folder to recent folders list.
        Pushes to front, prevents duplicates, trims to max_items.
        """
        normalized = os.path.normpath(folder_path)
        recent = self._data.get("recent_folders", [])
        if normalized in recent:
            recent.remove(normalized)
        recent.insert(0, normalized)
        self._data["recent_folders"] = recent[:max_items]
        self.save()

    def add_recent_folder(self, folder_path: str, max_items: int = 200) -> None:
        self.add_folder(folder_path, max_items)

    def remove_recent_folder(self, folder_path: str) -> bool:
        """Remove a path from quick access without touching files on disk."""
        normalized = os.path.normcase(os.path.normpath(folder_path))
        folders = self._data.get("recent_folders", [])
        kept = [path for path in folders if os.path.normcase(os.path.normpath(path)) != normalized]
        changed = len(kept) != len(folders)
        if changed:
            self._data["recent_folders"] = kept
            aliases = self._data.get("folder_aliases", {})
            if isinstance(aliases, dict):
                aliases.pop(normalized, None)
            self.save()
        return changed

    def get_recent_folders(self) -> List[str]:
        return list(self._data.get("recent_folders", []))

    @staticmethod
    def _folder_key(folder_path: str) -> str:
        return os.path.normcase(os.path.normpath(str(folder_path)))

    def get_folder_alias(self, folder_path: str) -> str:
        aliases = self._data.get("folder_aliases", {})
        return str(aliases.get(self._folder_key(folder_path), "")) if isinstance(aliases, dict) else ""

    def set_folder_alias(self, folder_path: str, alias: str) -> None:
        aliases = self._data.setdefault("folder_aliases", {})
        if not isinstance(aliases, dict):
            aliases = {}
            self._data["folder_aliases"] = aliases
        key = self._folder_key(folder_path)
        value = str(alias or "").strip()
        if value:
            aliases[key] = value
        else:
            aliases.pop(key, None)
        self.save()

    def clear_history(self) -> None:
        """Remove all entries from the recent folders list."""
        self._data["recent_folders"] = []
        self.save()

    def record_connection(self, session, event: str, max_items: int = 200) -> None:
        """Record server session lifecycle without storing passwords or secrets."""
        if event not in {"started", "stopped"}:
            raise ValueError("event harus 'started' atau 'stopped'")
        item = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "host": str(session.host_ip or ""),
            "port": int(session.port),
            "share": str(session.share_name),
            "folder_path": str(session.folder_path),
            "folder_name": self.get_folder_alias(session.folder_path) or Path(session.folder_path).name,
            "read_only": bool(session.read_only),
        }
        history = self._data.setdefault("connection_history", [])
        history.insert(0, item)
        self._data["connection_history"] = history[:max_items]
        self.save()

    def get_connection_history(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._data.get("connection_history", []) if isinstance(item, dict)]

    def clear_connection_history(self) -> None:
        self._data["connection_history"] = []
        self.save()

    def get_transfer_history(self, max_items: int = 2000) -> List[Dict[str, Any]]:
        """Read recent file I/O events recorded by the detached SMB service."""
        try:
            if not TRANSFER_HISTORY_PATH.exists():
                return []
            lines = TRANSFER_HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-max_items:]
            events = []
            for line in lines:
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(event, dict) and event.get("direction") in {"upload", "download"}:
                    events.append(event)
            return list(reversed(events))
        except OSError:
            logger.exception("Failed to read SMB transfer history")
            return []

    def clear_transfer_history(self) -> None:
        try:
            TRANSFER_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            TRANSFER_HISTORY_PATH.write_text("", encoding="utf-8")
        except OSError:
            logger.exception("Failed to clear SMB transfer history")

    def get_settings(self) -> Dict[str, Any]:
        return dict(self._data.get("settings", {}))

    def update_settings(self, **kwargs) -> None:
        self._data["settings"].update(kwargs)
        self.save()

    def export_backup(self, target_file: str | Path) -> None:
        """
        Export history and settings to a JSON file.
        SECURITY: Explicitly filters out any credentials/passwords.
        """
        backup_data = {
            "version": "1.0",
            "recent_folders": self._data.get("recent_folders", []),
            "settings": {
                k: v for k, v in self._data.get("settings", {}).items()
                if not any(secret_term in k.lower() for secret_term in ["pass", "token", "cred", "secret", "user"])
            }
        }
        target_path = Path(target_file)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

    def import_backup(self, source_file: str | Path) -> ImportResult:
        """
        Import folders and settings from a JSON backup file.
        Merges folders, ignores duplicates, returns ImportResult.
        """
        source_path = Path(source_file)
        if not source_path.exists():
            return ImportResult(success=False, error=f"File tidak ditemukan: {source_path}")

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return ImportResult(success=False, error=f"Format JSON tidak valid: {e}")

        if not isinstance(data, dict):
            return ImportResult(success=False, error="Struktur file cadangan tidak valid (harus objek JSON)")

        incoming_folders = data.get("recent_folders", [])
        if not isinstance(incoming_folders, list):
            return ImportResult(success=False, error="'recent_folders' harus berupa list")

        current = self._data.get("recent_folders", [])
        imported_count = 0
        for f in incoming_folders:
            if isinstance(f, str):
                norm = os.path.normpath(f)
                if norm not in current:
                    current.append(norm)
                    imported_count += 1

        self._data["recent_folders"] = current

        incoming_settings = data.get("settings", {})
        if isinstance(incoming_settings, dict):
            clean_settings = {
                k: v for k, v in incoming_settings.items()
                if not any(secret_term in k.lower() for secret_term in ["pass", "token", "cred", "secret", "user"])
            }
            self._data["settings"].update(clean_settings)

        self.save()
        return ImportResult(
            success=True,
            imported_count=imported_count,
            message=f"Berhasil mengimpor {imported_count} riwayat folder baru."
        )
