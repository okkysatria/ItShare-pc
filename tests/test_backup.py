"""
tests/test_backup.py - Unit tests for history, backup export, and import.
"""
import json
import pytest
from pathlib import Path
from core.history import HistoryManager

@pytest.fixture
def temp_config_file(tmp_path):
    return tmp_path / "config.json"

@pytest.fixture
def history_mgr(temp_config_file):
    return HistoryManager(config_path=temp_config_file)

def test_add_and_get_recent_folders(history_mgr):
    history_mgr.add_folder("C:\\Test1")
    history_mgr.add_folder("C:\\Test2")
    history_mgr.add_folder("C:\\Test1")

    folders = history_mgr.get_recent_folders()
    assert len(folders) == 2
    assert folders[0] == "C:\\Test1"
    assert folders[1] == "C:\\Test2"

def test_export_backup_no_sensitive_data(history_mgr, tmp_path):
    history_mgr.add_folder("D:\\Photos")
    history_mgr.update_settings(default_port=5000, secret_key="ShouldNotExport", user_token="HideMe")

    export_path = tmp_path / "backup.json"
    history_mgr.export_backup(export_path)

    assert export_path.exists()
    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "recent_folders" in data
    assert "D:\\Photos" in data["recent_folders"]
    assert "secret_key" not in data["settings"]
    assert "user_token" not in data["settings"]
    assert data["settings"]["default_port"] == 5000

def test_import_backup_roundtrip_and_deduplicate(history_mgr, tmp_path):
    history_mgr.add_folder("C:\\FolderA")
    backup_file = tmp_path / "backup_roundtrip.json"
    history_mgr.export_backup(backup_file)

    new_config = tmp_path / "new_config.json"
    new_mgr = HistoryManager(config_path=new_config)
    new_mgr.add_folder("C:\\FolderB")

    res = new_mgr.import_backup(backup_file)
    assert res.success is True
    assert res.imported_count == 1

    folders = new_mgr.get_recent_folders()
    assert "C:\\FolderA" in folders
    assert "C:\\FolderB" in folders

    res2 = new_mgr.import_backup(backup_file)
    assert res2.success is True
    assert res2.imported_count == 0

def test_import_invalid_file(history_mgr, tmp_path):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("invalid json content!", encoding="utf-8")

    res = history_mgr.import_backup(bad_file)
    assert res.success is False
    assert "Format JSON tidak valid" in res.error

    missing_file = tmp_path / "non_existent.json"
    res_missing = history_mgr.import_backup(missing_file)
    assert res_missing.success is False
    assert "tidak ditemukan" in res_missing.error
