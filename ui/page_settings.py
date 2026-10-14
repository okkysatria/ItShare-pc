"""
ui/page_settings.py — Application settings page.
"""
import logging
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QFormLayout, QSpinBox, QCheckBox, QComboBox,
    QLineEdit, QScrollArea
)

logger = logging.getLogger(__name__)

class PageSettings(QWidget):
    settings_saved = Signal(dict)

    def __init__(self, history_manager=None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self._loading_settings = True
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self._save_settings)
        self._build_ui()
        self._load_settings()
        self._loading_settings = False
        self._connect_auto_save()

    def _build_ui(self):
        check_icon = (Path(__file__).resolve().parent.parent / "assets" / "checkmark_white.svg").as_posix()
        self.setStyleSheet(
            "QCheckBox::indicator:checked { "
            "image: url(\"" + check_icon + "\"); }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet("QFrame { background:#ffffff; border-bottom:1px solid #dfe5df; }")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("Pengaturan")
        lbl.setStyleSheet("font-size:16px; font-weight:700; color:#1e293b;")
        tb_lay.addWidget(lbl)
        root.addWidget(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QFrame()
        scroll_content.setStyleSheet("background:#f5f7f3;")
        c_lay = QVBoxLayout(scroll_content)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(20)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        grp_server = QGroupBox("Default Server")
        form_s = QFormLayout(grp_server)
        form_s.setSpacing(10)

        self.spin_default_port = QSpinBox()
        self.spin_default_port.setRange(1024, 65535)
        self.spin_default_port.setValue(4455)
        self.spin_default_port.setFixedWidth(100)
        form_s.addRow("Port Default:", self.spin_default_port)

        self.chk_default_ro = QCheckBox("Read-Only secara default")
        self.chk_default_ro.setChecked(True)
        form_s.addRow(self.chk_default_ro)

        self.spin_default_timeout = QSpinBox()
        self.spin_default_timeout.setRange(0, 8760)
        self.spin_default_timeout.setValue(0)
        self.spin_default_timeout.setFixedWidth(120)
        timeout_row = QWidget()
        timeout_layout = QHBoxLayout(timeout_row)
        timeout_layout.setContentsMargins(0, 0, 0, 0)
        timeout_layout.addWidget(self.spin_default_timeout)
        timeout_layout.addWidget(QLabel("jam"))
        timeout_layout.addStretch()
        form_s.addRow("Batas Waktu Default:", timeout_row)

        c_lay.addWidget(grp_server)

        grp_app = QGroupBox("Aplikasi & Tampilan")
        form_app = QFormLayout(grp_app)
        form_app.setSpacing(10)

        self.combo_startup_page = QComboBox()
        self.combo_startup_page.addItem("Dashboard", 0)
        self.combo_startup_page.addItem("Riwayat", 1)
        self.combo_startup_page.addItem("Pengaturan", 2)
        form_app.addRow("Halaman saat dibuka:", self.combo_startup_page)

        self.combo_page_size = QComboBox()
        for count in (8, 12, 20):
            self.combo_page_size.addItem(f"{count} folder per halaman", count)
        form_app.addRow("Jumlah folder per halaman:", self.combo_page_size)

        self.combo_theme = QComboBox()
        self.combo_theme.addItem("Ikuti tema Windows", "system")
        self.combo_theme.addItem("Terang", "light")
        self.combo_theme.addItem("Gelap", "dark")
        form_app.addRow("Tema aplikasi:", self.combo_theme)

        self.combo_language = QComboBox()
        self.combo_language.addItem("English", "en")
        self.combo_language.addItem("Bahasa Indonesia", "id")
        form_app.addRow("Bahasa:", self.combo_language)

        self.chk_show_folder_paths = QCheckBox("Tampilkan lokasi folder di Dashboard")
        self.chk_show_folder_paths.setChecked(True)
        form_app.addRow(self.chk_show_folder_paths)

        self.chk_hide_qr_by_default = QCheckBox("Sembunyikan QR secara default")
        self.chk_hide_qr_by_default.setToolTip("QR akan diburamkan setiap kali sesi berbagi dimulai.")
        form_app.addRow(self.chk_hide_qr_by_default)

        self.chk_confirm_stop = QCheckBox("Konfirmasi sebelum menghentikan share")
        form_app.addRow(self.chk_confirm_stop)
        self.chk_keep_share = QCheckBox("Pertahankan share saat aplikasi ditutup")
        form_app.addRow(self.chk_keep_share)
        c_lay.addWidget(grp_app)

        scroll.setWidget(scroll_content)
        root.addWidget(scroll, stretch=1)

    def _connect_auto_save(self):
        for widget, signal in (
            (self.spin_default_port, self.spin_default_port.valueChanged),
            (self.chk_default_ro, self.chk_default_ro.toggled),
            (self.spin_default_timeout, self.spin_default_timeout.valueChanged),
            (self.combo_startup_page, self.combo_startup_page.currentIndexChanged),
            (self.combo_page_size, self.combo_page_size.currentIndexChanged),
            (self.combo_theme, self.combo_theme.currentIndexChanged),
            (self.combo_language, self.combo_language.currentIndexChanged),
            (self.chk_show_folder_paths, self.chk_show_folder_paths.toggled),
            (self.chk_hide_qr_by_default, self.chk_hide_qr_by_default.toggled),
            (self.chk_confirm_stop, self.chk_confirm_stop.toggled),
            (self.chk_keep_share, self.chk_keep_share.toggled),
        ):
            signal.connect(self._schedule_save)

    def _schedule_save(self, *_):
        if not self._loading_settings:
            self._save_timer.start()

    def _load_settings(self):
        settings = self.history_manager.get_settings() if self.history_manager else {}
        self.spin_default_port.setValue(int(settings.get("default_port", 4455)))
        self.chk_default_ro.setChecked(bool(settings.get("default_read_only", True)))
        timeout_minutes = max(0, int(settings.get("default_timeout_minutes", 0)))
        self.spin_default_timeout.setValue(min(8760, (timeout_minutes + 59) // 60))
        self.combo_startup_page.setCurrentIndex(
            max(0, self.combo_startup_page.findData(int(settings.get("startup_page", 0))))
        )
        self.combo_page_size.setCurrentIndex(
            max(0, self.combo_page_size.findData(int(settings.get("folders_per_page", 8))))
        )
        self.combo_theme.setCurrentIndex(max(0, self.combo_theme.findData(settings.get("theme", "system"))))
        self.combo_language.setCurrentIndex(max(0, self.combo_language.findData(settings.get("language", "en"))))
        self.chk_show_folder_paths.setChecked(bool(settings.get("show_folder_paths", True)))
        self.chk_hide_qr_by_default.setChecked(bool(settings.get("hide_qr_by_default", False)))
        self.chk_confirm_stop.setChecked(bool(settings.get("confirm_before_stop", True)))
        self.chk_keep_share.setChecked(bool(settings.get("keep_share_after_exit", True)))

    def _save_settings(self):
        if not self.history_manager:
            return
        self.history_manager.update_settings(
            default_port=self.spin_default_port.value(),
            default_read_only=self.chk_default_ro.isChecked(),
            default_timeout_minutes=self.spin_default_timeout.value() * 60,
            startup_page=int(self.combo_startup_page.currentData()),
            folders_per_page=int(self.combo_page_size.currentData()),
            theme=str(self.combo_theme.currentData()),
            language=str(self.combo_language.currentData()),
            show_folder_paths=self.chk_show_folder_paths.isChecked(),
            hide_qr_by_default=self.chk_hide_qr_by_default.isChecked(),
            confirm_before_stop=self.chk_confirm_stop.isChecked(),
            keep_share_after_exit=self.chk_keep_share.isChecked(),
        )
        self.settings_saved.emit(self.history_manager.get_settings())
