"""
tests/test_ui_flow.py - UI flow integration tests.
"""
import pytest
from unittest.mock import patch
from ui.main_window import MainWindow


@pytest.fixture
def isolated_main_window(qtbot, monkeypatch, tmp_path):
    """MainWindow with an isolated config path — never writes to ~/.itshare/config.json."""
    monkeypatch.setattr("core.history.DEFAULT_CONFIG_PATH", tmp_path / "test_config.json")
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_initial_state(isolated_main_window):
    assert isolated_main_window.stack.currentIndex() == 0
    assert isolated_main_window.top_bar.btn_folders.isChecked() is True
    assert isolated_main_window.top_bar.btn_history.isChecked() is False
    assert isolated_main_window.top_bar.btn_settings.isChecked() is False
    assert isolated_main_window.page_folders is not None


def test_path_traversal_validation(isolated_main_window):
    from ui.dialogs import AddShareDialog
    dlg = AddShareDialog(folder_path="../../etc/passwd", parent=isolated_main_window)
    dlg.radio_existing.setChecked(True)
    dlg.txt_folder.setText("../../etc/passwd")
    with patch("ui.dialogs.QMessageBox.warning"):
        dlg._on_accept()
    assert dlg.result() != 1


def test_session_lifecycle_ui(qtbot, monkeypatch, tmp_path):
    """Server lifecycle test with isolated config to prevent temp paths leaking into user data."""
    monkeypatch.setattr("core.history.DEFAULT_CONFIG_PATH", tmp_path / "test_config.json")
    win = MainWindow()
    qtbot.addWidget(win)

    shared_folder = tmp_path / "ui_shared"
    shared_folder.mkdir()

    from core.session import ShareSession
    session = ShareSession(
        folder_path=str(shared_folder),
        username="testuser",
        password="testpass1234",
        port=14460,
        read_only=True,
    )

    win.page_folders._launch_server(session)
    assert win.smb_manager.is_running() is True
    assert "14460" in win.top_bar.lbl_speed.text()

    win.page_folders.on_stop_share()
    assert win.smb_manager.is_running() is False
