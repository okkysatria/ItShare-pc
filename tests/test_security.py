"""
tests/test_security.py - Security and path traversal tests.
"""
import os
import pytest
from core.credentials import generate_username, generate_password
from core.session import ShareSession
from ui.tab_setup import TabSetup
from core.history import HistoryManager
from core.smb_server import SMBServerManager

def test_credentials_entropy():

    for _ in range(50):
        u = generate_username(8)
        assert len(u) == 8
        assert u.isalnum()
        p = generate_password(16)
        assert len(p) == 16
        assert p.isalnum()

def test_path_traversal_rejection(tmp_path, qtbot):
    history_mgr = HistoryManager(config_path=tmp_path / "cfg.json")
    smb_mgr = SMBServerManager()
    tab = TabSetup(smb_mgr, history_mgr)
    qtbot.addWidget(tab)

    bad_paths = [
        "../test",
        "..\\windows",
        "C:\\Users\\..\\..\\Windows",
        "../../../../etc/passwd",
        "",
        "   "
    ]
    for p in bad_paths:
        assert tab._validate_path(p) is False

def test_valid_directory_acceptance(tmp_path, qtbot):
    valid_dir = tmp_path / "valid_share"
    valid_dir.mkdir()

    history_mgr = HistoryManager(config_path=tmp_path / "cfg.json")
    smb_mgr = SMBServerManager()
    tab = TabSetup(smb_mgr, history_mgr)
    qtbot.addWidget(tab)

    assert tab._validate_path(str(valid_dir)) is True

    assert tab._validate_path(str(tmp_path / "non_existent_dir")) is False
