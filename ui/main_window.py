"""Main ItShare desktop window with Dashboard, Riwayat, and Pengaturan."""

import logging
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QMessageBox, QStatusBar
)
from PySide6.QtGui import QCloseEvent, QAction, QFont, QPixmap, QIcon

from core.smb_server import SMBServerManager
from core.history import HistoryManager
from core.session import ShareSession
from ui.styles import MAIN_STYLE, BTN_SIDEBAR, apply_theme, theme_stylesheet
from ui.i18n import apply_language, translate

logger = logging.getLogger(__name__)

class NavigationButton(QPushButton):
    def __init__(self, icon_file: str, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.icon_file = icon_file
        icon_path = Path(__file__).resolve().parent.parent / "assets" / icon_file
        self.setIcon(QIcon(str(icon_path)))
        self.setIconSize(QSize(18, 18))
        self.setText(label)
        self.setStyleSheet(BTN_SIDEBAR)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12))

    def set_icon_theme(self, dark: bool):
        base_name = Path(self.icon_file).stem.removesuffix("_dark")
        icon_path = Path(__file__).resolve().parent.parent / "assets" / f"{base_name}{'_dark' if dark else ''}.svg"
        if icon_path.is_file():
            self.setIcon(QIcon(str(icon_path)))

class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setStyleSheet("""
            TopBar {
                background-color: #ffffff;
                border-bottom: 1px solid #dfe5df;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        logo = QLabel()
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "itshare_logo.png"
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap.scaledToHeight(38, Qt.TransformationMode.SmoothTransformation))
            logo.setFixedSize(114, 42)
            logo.setScaledContents(False)
            layout.addWidget(logo)
        else:
            logo.setText("ItShare")
            logo.setStyleSheet("font-size:17px; font-weight:700; color:#17211c;")
            layout.addWidget(logo)

        self.btn_folders = NavigationButton("icon_dashboard.svg", "Dashboard", self)
        self.btn_history = NavigationButton("icon_history.svg", "Riwayat", self)
        self.btn_settings = NavigationButton("icon_settings.svg", "Pengaturan", self)
        self.btn_folders.setToolTip("Dashboard · Ctrl+1")
        self.btn_history.setToolTip("Riwayat · Ctrl+2")
        self.btn_settings.setToolTip("Pengaturan · Ctrl+3")
        for button in (self.btn_folders, self.btn_history, self.btn_settings):
            button.setFixedHeight(36)
            button.setFont(QFont("Segoe UI", 10))
            layout.addWidget(button)

        layout.addStretch()

        self.lbl_speed = QLabel("● Tidak ada sesi aktif")
        self.lbl_speed.setStyleSheet("color: #68756e; font-size: 12px;")
        layout.addWidget(self.lbl_speed)

    def set_status_running(self, ip: str, port: int):
        self.lbl_speed.setText(f"● Aktif  {ip}:{port}")
        self.lbl_speed.setStyleSheet("color: #176b49; font-size: 12px; font-weight: 600;")

    def set_status_idle(self):
        self.lbl_speed.setText("● Tidak ada sesi aktif")
        self.lbl_speed.setStyleSheet("color: #68756e; font-size: 12px;")

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ItShare")
        self.resize(1100, 700)
        self.setMinimumSize(680, 500)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "itshare_logo_mark.png"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setStyleSheet(MAIN_STYLE)

        self.smb_manager = SMBServerManager()
        self.history_manager = HistoryManager()
        self._build_menubar()
        self._build_ui()
        self._apply_app_settings(self.history_manager.get_settings())

    def _build_menubar(self):
        mb = self.menuBar()

        m_file = mb.addMenu("File")
        a_add = QAction("Tambah Folder Baru...", self)
        a_add.setShortcut("Ctrl+N")
        a_add.triggered.connect(self._action_add_folder)
        m_file.addAction(a_add)

        a_backup = QAction("Ekspor Backup...", self)
        a_backup.triggered.connect(self._action_export_backup)
        m_file.addAction(a_backup)

        a_import = QAction("Impor Backup...", self)
        a_import.triggered.connect(self._action_import_backup)
        m_file.addAction(a_import)

        m_file.addSeparator()
        a_quit = QAction("Keluar", self)
        a_quit.setShortcut("Ctrl+Q")
        a_quit.triggered.connect(self.close)
        m_file.addAction(a_quit)

        m_share = mb.addMenu("Bagikan")
        a_show_qr = QAction("Tampilkan QR SMB...", self)
        a_show_qr.setShortcut("Ctrl+Shift+Q")
        a_show_qr.triggered.connect(self._action_show_qr)
        m_share.addAction(a_show_qr)

        a_wifi_qr = QAction("Tampilkan QR WiFi...", self)
        a_wifi_qr.triggered.connect(self._action_show_wifi_qr)
        m_share.addAction(a_wifi_qr)

        m_help = mb.addMenu("Bantuan")
        a_about = QAction("Tentang ItShare", self)
        a_about.triggered.connect(self._action_about)
        m_help.addAction(a_about)

    def _build_ui(self):

        from ui.page_folders import PageFolders
        from ui.page_history import PageHistory
        from ui.page_settings import PageSettings

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.top_bar = TopBar()
        root_layout.addWidget(self.top_bar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.page_folders  = PageFolders(self.smb_manager, self.history_manager)
        self.page_history  = PageHistory(self.history_manager, self.smb_manager)
        self.page_settings = PageSettings(self.history_manager)
        self.page_settings.settings_saved.connect(self._apply_app_settings)
        self.page_folders.apply_ui_preferences(self.history_manager.get_settings())

        self.stack.addWidget(self.page_folders)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_settings)
        body_layout.addWidget(self.stack, stretch=1)

        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._status_source_message = "Siap. Pilih folder pada Dashboard untuk mulai berbagi."
        self._set_status_message(self._status_source_message)

        nav_btns = [
            self.top_bar.btn_folders,
            self.top_bar.btn_history,
            self.top_bar.btn_settings,
        ]
        for i, btn in enumerate(nav_btns):
            btn.clicked.connect(lambda checked, idx=i: self._nav(idx))

        self.page_folders.session_started.connect(self._on_session_started)
        self.page_folders.session_stopped.connect(self._on_session_stopped)
        self.page_folders.session_started.connect(lambda *_: self.page_history.refresh())
        self.page_folders.session_stopped.connect(self.page_history.refresh)
        for index, button in enumerate((self.top_bar.btn_folders, self.top_bar.btn_history, self.top_bar.btn_settings), start=1):
            shortcut = QAction(self)
            shortcut.setShortcut(f"Ctrl+{index}")
            shortcut.triggered.connect(lambda checked=False, page=index - 1: self._nav(page))
            self.addAction(shortcut)

        startup_page = max(0, min(2, int(self.history_manager.get_settings().get("startup_page", 0))))
        self._nav(startup_page)
        active_sessions = self.smb_manager.active_sessions
        if active_sessions and self.smb_manager.is_running():
            self.page_folders.restore_active_sessions(active_sessions)
            self._on_session_started(active_sessions[0])

    def _nav(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.page_history.refresh()
        nav_btns = [
            self.top_bar.btn_folders,
            self.top_bar.btn_history,
            self.top_bar.btn_settings,
        ]
        for i, btn in enumerate(nav_btns):
            btn.setChecked(i == index)

    def _apply_app_settings(self, settings: dict):
        self.page_folders.apply_ui_preferences(settings)
        theme = settings.get("theme", "system")
        apply_theme(self, theme)
        dark = theme_stylesheet(theme) != MAIN_STYLE
        self.page_folders.set_icon_theme(dark)
        self.page_folders.set_dark_mode(dark)
        for button in (self.top_bar.btn_folders, self.top_bar.btn_history, self.top_bar.btn_settings):
            button.set_icon_theme(dark)
        apply_language(self, settings.get("language", "en"))
        self.status_bar.showMessage(translate(self._status_source_message, settings.get("language", "en")))

    def _set_status_message(self, message: str):
        self._status_source_message = message
        language = self.history_manager.get_settings().get("language", "en")
        self.status_bar.showMessage(translate(message, language))

    def _on_session_started(self, session: ShareSession):
        self.top_bar.set_status_running(session.host_ip or "127.0.0.1", session.port)
        self._set_status_message(
            f"● Server aktif  smb://{session.host_ip}:{session.port}/{session.share_name}  |  "
            f"User: {session.username}  |  Mode: {'Hanya Baca' if session.read_only else 'Baca-Tulis'}"
        )
        apply_language(self, self.history_manager.get_settings().get("language", "en"))
        self._nav(0)

    def _on_session_stopped(self):
        self.top_bar.set_status_idle()
        self._set_status_message("● Server dihentikan. Siap untuk sesi baru.")
        apply_language(self, self.history_manager.get_settings().get("language", "en"))
        self._nav(0)

    def _on_disconnect(self):
        self.page_folders.on_regenerate()
        self._set_status_message("Kredensial diperbarui. Klien lama terputus.")

    def _on_reset(self):
        self.page_folders.on_stop_share()
        self._nav(0)
        self._set_status_message("Sesi direset. Pilih folder untuk mulai berbagi.")

    def _action_add_folder(self):
        self._nav(0)
        self.page_folders.focus_add_folder()

    def _action_export_backup(self):
        self._nav(0)
        self.page_folders.export_backup()

    def _action_import_backup(self):
        self._nav(0)
        self.page_folders.import_backup()

    def _action_show_qr(self):
        self._nav(0)
        self.page_folders.show_qr_dialog()

    def _action_show_wifi_qr(self):
        self._nav(0)
        self.page_folders.show_wifi_dialog()

    def _action_about(self):
        english = self.history_manager.get_settings().get("language", "en") != "id"
        QMessageBox.about(
            self,
            "About ItShare" if english else "Tentang ItShare",
            "<b>ItShare</b> v1.0.0-M3<br><br>"
            + ("Share PC folders with your phone over SMB.<br>Scan the QR code to connect.<br><br>"
               if english else "Bagikan folder PC ke HP melalui SMB.<br>Pindai QR untuk terhubung.<br><br>")
            + "Python · PySide6 · impacket · qrcode"
        )

    def closeEvent(self, event: QCloseEvent):
        if self.smb_manager.is_running():
            settings = self.history_manager.get_settings()
            if settings.get("keep_share_after_exit", True):

                event.accept()
                return

            reply = QMessageBox.question(
                self,
                "Konfirmasi Keluar",
                "Server SMB sedang berjalan.\nMenutup aplikasi akan memutuskan semua klien.\n\nYakin ingin keluar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.page_folders.on_stop_share(confirm=False)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
