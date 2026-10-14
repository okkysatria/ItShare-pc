"""
core/session.py - Session state dataclass for ItShare.
"""
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class ShareSession:
    folder_path: str
    username: str
    password: str
    port: int = 4455
    read_only: bool = True
    timeout_minutes: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "stopped"
    share_name: str = "SHARE"
    host_ip: Optional[str] = None

    @property
    def expires_at(self) -> int:
        """
        Returns Unix timestamp (epoch seconds int) when session expires,
        or 0 if permanent (timeout_minutes == 0).
        """
        if self.timeout_minutes <= 0:
            return 0
        return int(self.created_at + (self.timeout_minutes * 60))

    @property
    def is_expired(self) -> bool:
        if self.timeout_minutes <= 0:
            return False
        return time.time() >= self.expires_at

    @property
    def remaining_seconds(self) -> int:
        if self.timeout_minutes <= 0:
            return 0
        rem = int(self.expires_at - time.time())
        return max(0, rem)
