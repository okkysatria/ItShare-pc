"""
ui/dialogs.py — All popup dialogs for ItShare.

Dialogs:
  AddShareDialog   — Setup form to configure and launch a new share
  itshareDialog    — QR code display popup (SMB credentials)
  WifiQrDialog     — WiFi QR code popup
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSpinBox, QComboBox, QFileDialog,
    QFormLayout, QFrame, QDialogButtonBox, QGroupBox,
    QTabWidget, QWidget, QMessageBox, QRadioButton, QButtonGroup,
    QSizePolicy, QScrollArea, QBoxLayout, QToolButton, QGridLayout
)
from PySide6.QtGui import QFont, QPixmap, QClipboard, QGuiApplication, QIcon

from core.session import ShareSession
from core.credentials import generate_username, generate_password
from core.network import get_local_ips, get_wifi_ssid
from core.qr_generator import build_smb_payload, build_wifi_payload, render_to_pixmap
from ui.styles import BTN_PRIMARY, BTN_DANGER, BTN_NORMAL, BTN_SUCCESS
from ui.i18n import translate

logger = logging.getLogger(__name__)

class AddShareDialog(QDialog):
    """
    Popup form to choose a folder and configure SMB share options.
    Returns a ready ShareSession on accept.
    """

    def __init__(self, folder_path: str = "", settings: Optional[dict] = None, parent=None, display_name: str = ""):
        super().__init__(parent)
        self.settings = settings or {}
        self.setWindowTitle("Bagikan Folder Baru")
        self.setMinimumSize(460, 420)
        self.setModal(True)
        self._language = "en"
        self._session: Optional[ShareSession] = None
        self._display_name = ""
        self._display_name_user_edited = bool(display_name)
        self._password_visible = False
        self._build_ui(folder_path, display_name)

    def _build_ui(self, initial_folder: str, initial_display_name: str = ""):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 10)
        root.setSpacing(8)

        header = QHBoxLayout()
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "itshare_logo_mark.png"
        logo = QLabel()
        logo.setPixmap(QPixmap(str(logo_path)).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(logo)
        title_box = QVBoxLayout()
        title = QLabel("Bagikan Folder Baru")
        title.setObjectName("setupTitle")
        title.setStyleSheet("font-size:19px; font-weight:700;")
        subtitle = QLabel("Pilih folder, lalu pindai QR dari Android. Hanya 3 langkah.")
        subtitle.setObjectName("setupSubtitle")
        subtitle.setStyleSheet("color:#68756e;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        root.addLayout(header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("setupBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 2, 4, 4)
        body_layout.setSpacing(8)

        folder_card = self._make_setup_card()
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setContentsMargins(12, 10, 12, 10)
        folder_layout.setSpacing(7)
        folder_layout.addWidget(self._step_heading("1", "Folder mana yang mau dibagikan?"))

        self.radio_existing = QRadioButton("Pilih folder yang sudah ada", self)
        self.radio_new = QRadioButton("Buat folder baru", self)
        self.radio_existing.setChecked(True)
        self.radio_existing.hide()
        self.radio_new.hide()
        self.txt_folder = QLineEdit(initial_folder, self)
        self.txt_folder.hide()

        self.existing_widget = QWidget()
        existing_layout = QVBoxLayout(self.existing_widget)
        existing_layout.setContentsMargins(0, 0, 0, 0)
        picker = QFrame()
        picker.setObjectName("folderPicker")
        picker_layout = QHBoxLayout(picker)
        picker_layout.setContentsMargins(10, 8, 10, 8)
        folder_icon = QLabel()
        folder_icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon_folder.svg"
        folder_icon.setPixmap(QIcon(str(folder_icon_path)).pixmap(32, 32))
        picker_layout.addWidget(folder_icon)
        folder_info = QVBoxLayout()
        self.lbl_folder_name = QLabel()
        self.lbl_folder_name.setObjectName("folderName")
        self.lbl_folder_path = QLabel()
        self.lbl_folder_path.setObjectName("setupSubtitle")
        self.lbl_folder_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_folder_path.setWordWrap(True)
        self.lbl_folder_path.setMinimumWidth(0)
        folder_info.addWidget(self.lbl_folder_name)
        folder_info.addWidget(self.lbl_folder_path)
        picker_layout.addLayout(folder_info, 1)
        self.btn_browse_folder = QPushButton("Pilih Folder")
        self.btn_browse_folder.setStyleSheet(BTN_NORMAL)
        self.btn_browse_folder.clicked.connect(self._browse_folder)
        picker_layout.addWidget(self.btn_browse_folder)
        existing_layout.addWidget(picker)
        self.txt_folder.textChanged.connect(self._update_folder_card)
        self.txt_folder.textChanged.connect(self._autofill_display_name)

        mode_row = QHBoxLayout()
        self.lbl_mode_prompt = QLabel("Belum punya folder?")
        self.btn_folder_mode = QPushButton("Buat folder baru")
        self.btn_folder_mode.setObjectName("setupLink")
        self.btn_folder_mode.clicked.connect(self._toggle_folder_mode)
        mode_row.addWidget(self.lbl_mode_prompt)
        mode_row.addWidget(self.btn_folder_mode)
        mode_row.addStretch(1)
        existing_layout.addLayout(mode_row)
        folder_layout.addWidget(self.existing_widget)

        self.new_widget = QWidget()
        new_form = QFormLayout(self.new_widget)
        new_form.setContentsMargins(0, 0, 0, 0)
        new_form.setHorizontalSpacing(10)
        new_form.setVerticalSpacing(8)
        self.txt_new_name = QLineEdit()
        self.txt_new_name.setPlaceholderText("Nama folder baru")
        self.txt_new_name.textChanged.connect(self._autofill_new_folder_display_name)
        self.txt_new_parent = QLineEdit(str(Path.home()))
        browse_parent = QPushButton("Pilih Lokasi")
        browse_parent.setStyleSheet(BTN_NORMAL)
        browse_parent.clicked.connect(self._browse_parent)
        parent_row = QHBoxLayout()
        parent_row.addWidget(self.txt_new_parent, 1)
        parent_row.addWidget(browse_parent)
        new_form.addRow("Nama folder", self.txt_new_name)
        new_form.addRow("Lokasi induk", parent_row)
        self.new_widget.hide()
        folder_layout.addWidget(self.new_widget)

        display_label = QLabel("Nama yang tampil di HP")
        display_label.setObjectName("setupFieldTitle")
        self.txt_display_name = QLineEdit(initial_display_name)
        self.txt_display_name.setPlaceholderText("Nama yang muncul di Android")
        self.txt_display_name.textEdited.connect(lambda _text: setattr(self, "_display_name_user_edited", True))
        display_hint = QLabel("Terisi otomatis dari nama folder. Boleh diganti.")
        display_hint.setObjectName("setupSubtitle")
        folder_layout.addWidget(display_label)
        folder_layout.addWidget(self.txt_display_name)
        folder_layout.addWidget(display_hint)
        body_layout.addWidget(folder_card)
        self._update_folder_card()
        if not initial_display_name and initial_folder:
            self._autofill_display_name(initial_folder)

        access_card = self._make_setup_card()
        access_layout = QVBoxLayout(access_card)
        access_layout.setContentsMargins(12, 10, 12, 10)
        access_layout.setSpacing(7)
        access_layout.addWidget(self._step_heading("2", "Atur akses dan waktu"))
        self.chk_readonly = QCheckBox(self)
        self.chk_readonly.setChecked(bool(self.settings.get("default_read_only", True)))
        self.chk_readonly.hide()
        access_group = QButtonGroup(self)
        access_group.setExclusive(True)
        self.rb_readonly = QRadioButton("Hanya lihat  ·  Disarankan")
        self.rb_writable = QRadioButton("Boleh ubah")
        access_group.addButton(self.rb_readonly)
        access_group.addButton(self.rb_writable)
        self.rb_readonly.setChecked(self.chk_readonly.isChecked())
        self.rb_writable.setChecked(not self.chk_readonly.isChecked())
        self.rb_readonly.toggled.connect(lambda checked: self.chk_readonly.setChecked(True) if checked else None)
        self.rb_writable.toggled.connect(lambda checked: self.chk_readonly.setChecked(False) if checked else None)
        access_grid = QGridLayout()
        access_grid.setHorizontalSpacing(10)
        for column, (radio, description) in enumerate((
            (self.rb_readonly, "HP bisa mengunduh, tetapi tidak bisa mengubah atau menghapus."),
            (self.rb_writable, "HP bisa mengunggah, membuat folder, dan menghapus."),
        )):
            option = QFrame()
            option.setObjectName("accessCard")
            option_layout = QVBoxLayout(option)
            option_layout.setContentsMargins(9, 8, 9, 8)
            option_layout.setSpacing(3)
            option_layout.addWidget(radio)
            description_label = QLabel(description)
            description_label.setObjectName("setupSubtitle")
            description_label.setWordWrap(True)
            option_layout.addWidget(description_label)
            radio.toggled.connect(lambda _checked, frame=option, button=radio: self._set_access_card_selected(frame, button.isChecked()))
            self._set_access_card_selected(option, radio.isChecked())
            access_grid.addWidget(option, 0, column)
        access_layout.addLayout(access_grid)

        duration_label = QLabel("Berapa lama dibagikan?")
        duration_label.setObjectName("setupFieldTitle")
        access_layout.addWidget(duration_label)
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(0, 8760)
        default_minutes = max(0, int(self.settings.get("default_timeout_minutes", 0)))
        default_hours = min(8760, (default_minutes + 59) // 60)
        self.spin_timeout.setValue(default_hours)
        duration_group = QButtonGroup(self)
        duration_group.setExclusive(True)
        duration_row = QHBoxLayout()
        duration_row.setSpacing(3)
        self.duration_buttons = {}
        for hours, label in ((0, "Tanpa batas"), (1, "1 jam"), (4, "4 jam"), (8, "8 jam")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("durationButton")
            button.clicked.connect(lambda _checked=False, value=hours: self._set_duration(value, False))
            duration_group.addButton(button)
            duration_row.addWidget(button, 1)
            self.duration_buttons[hours] = button
        self.btn_custom_duration = QPushButton("Lainnya")
        self.btn_custom_duration.setCheckable(True)
        self.btn_custom_duration.setObjectName("durationButton")
        self.btn_custom_duration.clicked.connect(lambda: self._set_duration(self.spin_timeout.value(), True))
        duration_group.addButton(self.btn_custom_duration)
        duration_row.addWidget(self.btn_custom_duration, 1)
        access_layout.addLayout(duration_row)
        self.custom_duration_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_duration_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.addWidget(QLabel("Durasi (jam)"))
        custom_layout.addWidget(self.spin_timeout)
        custom_layout.addStretch(1)
        is_custom = default_hours not in self.duration_buttons
        self.custom_duration_widget.setVisible(is_custom)
        if is_custom:
            self.btn_custom_duration.setChecked(True)
        else:
            self.duration_buttons[default_hours].setChecked(True)
        access_layout.addWidget(self.custom_duration_widget)
        body_layout.addWidget(access_card)

        advanced_card = self._make_setup_card()
        advanced_layout = QVBoxLayout(advanced_card)
        advanced_layout.setContentsMargins(12, 8, 12, 8)
        heading = QHBoxLayout()
        heading.addWidget(self._step_number("3"))
        advanced_text = QVBoxLayout()
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("Pengaturan lanjutan  ·  Opsional")
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setObjectName("advancedToggle")
        self.advanced_summary = QLabel()
        self.advanced_summary.setObjectName("setupSubtitle")
        advanced_text.addWidget(self.advanced_toggle)
        advanced_text.addWidget(self.advanced_summary)
        heading.addLayout(advanced_text, 1)
        advanced_layout.addLayout(heading)

        self.advanced_widget = QWidget()
        advanced_form = QVBoxLayout(self.advanced_widget)
        advanced_form.setContentsMargins(0, 14, 0, 0)
        advanced_form.setSpacing(8)
        network_grid = QGridLayout()
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(int(self.settings.get("default_port", 4455)))
        self.combo_iface = QComboBox()
        ips = get_local_ips()
        for iface, ip in ips:
            self.combo_iface.addItem(f"{iface}  ({ip})", ip)
        if not ips:
            self.combo_iface.addItem("Tidak terdeteksi", "127.0.0.1")
        network_grid.addWidget(QLabel("Port"), 0, 0)
        network_grid.addWidget(QLabel("Jaringan"), 0, 1)
        network_grid.addWidget(self.spin_port, 1, 0)
        network_grid.addWidget(self.combo_iface, 1, 1)
        advanced_form.addLayout(network_grid)
        port_hint = QLabel("Ganti hanya jika port sedang dipakai aplikasi lain.")
        port_hint.setObjectName("setupSubtitle")
        advanced_form.addWidget(port_hint)
        advanced_form.addWidget(QLabel("Pengguna dan kata sandi (otomatis)"))
        credentials_row = QHBoxLayout()
        self.lbl_user = QLineEdit()
        self.lbl_user.setReadOnly(True)
        self.lbl_pass = QLineEdit()
        self.lbl_pass.setReadOnly(True)
        self.lbl_pass.setEchoMode(QLineEdit.EchoMode.Password)
        credentials_row.addWidget(self.lbl_user, 1)
        credentials_row.addWidget(self.lbl_pass, 1)
        advanced_form.addLayout(credentials_row)
        credential_buttons = QHBoxLayout()
        self.btn_show_password = QPushButton("Tampilkan")
        self.btn_show_password.setStyleSheet(BTN_NORMAL)
        self.btn_show_password.clicked.connect(self._toggle_password_visibility)
        regen = QPushButton("Buat Ulang")
        regen.setStyleSheet(BTN_NORMAL)
        regen.clicked.connect(self._generate_credentials)
        credential_buttons.addWidget(self.btn_show_password)
        credential_buttons.addWidget(regen)
        credential_buttons.addStretch(1)
        advanced_form.addLayout(credential_buttons)
        self.advanced_widget.hide()
        advanced_layout.addWidget(self.advanced_widget)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.spin_port.valueChanged.connect(self._update_advanced_summary)
        self.combo_iface.currentIndexChanged.connect(self._update_advanced_summary)
        body_layout.addWidget(advanced_card)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        self._update_advanced_summary()
        self._generate_credentials()

        footer = QHBoxLayout()
        footer_hint = QLabel("Berkas hanya tersedia di jaringan lokal.")
        footer_hint.setObjectName("setupSubtitle")
        footer_hint.setWordWrap(True)
        footer_hint.setStyleSheet("color:#68756e;")
        footer.addWidget(footer_hint, 1)
        cancel = QPushButton("Batal")
        cancel.setStyleSheet(BTN_NORMAL)
        cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Mulai Berbagi")
        self.btn_ok.setStyleSheet(BTN_PRIMARY)
        self.btn_ok.clicked.connect(self._on_accept)
        footer.addWidget(cancel)
        footer.addWidget(self.btn_ok)
        root.addLayout(footer)

        body.setStyleSheet("""
            QWidget#setupBody { background-color: #f5f7f3; }
            QLabel#setupTitle { font-size: 19px; font-weight: 700; }
            QLabel#setupSubtitle { color: #68756e; }
            QLabel#setupFieldTitle { font-size: 14px; font-weight: 600; margin-top: 2px; }
            QLabel#folderName { font-size: 15px; font-weight: 650; }
            QFrame#setupCard { background: #ffffff; border: 1px solid #dfe5df; border-radius: 12px; }
            QFrame#folderPicker { background: #f6f9f7; border: 2px dashed #176b49; border-radius: 11px; }
            QFrame#accessCard { background: #ffffff; border: 2px solid #dfe5df; border-radius: 11px; }
            QFrame#accessCard[selected="true"] { background: #edf8f1; border-color: #176b49; }
            QPushButton#setupLink { border: none; background: transparent; color: #176b49; padding: 0; font-weight: 650; }
            QPushButton#setupLink:hover { text-decoration: underline; }
            QToolButton#advancedToggle { border: none; background: transparent; font-size: 15px; font-weight: 650; text-align: left; }
            QPushButton#durationButton { border: none; border-radius: 10px; padding: 7px 4px; color: #176b49; background: #edf3ef; }
            QPushButton#durationButton:checked { color: #ffffff; background: #176b49; font-weight: 650; }
        """)
        screen = self.screen()
        if screen:
            available = screen.availableGeometry()
            self.resize(min(760, max(460, available.width() - 48)), min(760, max(420, available.height() - 72)))
        else:
            self.resize(700, 680)

    @staticmethod
    def _make_setup_card():
        card = QFrame()
        card.setObjectName("setupCard")
        return card

    def _step_number(self, number: str):
        badge = QLabel(number)
        badge.setObjectName("stepNumber")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(38, 38)
        badge.setStyleSheet("background:#0c806e; color:white; border-radius:19px; font-size:17px; font-weight:700;")
        return badge

    def _step_heading(self, number: str, title: str):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 4)
        row_layout.setSpacing(12)
        row_layout.addWidget(self._step_number(number))
        label = QLabel(title)
        label.setStyleSheet("font-size:18px; font-weight:650;")
        row_layout.addWidget(label, 1)
        return row

    def _update_folder_card(self, *_):
        language = self.property("_itshare_language") or "en"
        path = self.txt_folder.text().strip()
        if os.path.isdir(path):
            self.lbl_folder_name.setText(Path(path).name or path)
            self.lbl_folder_path.setText(path)
        else:
            self.lbl_folder_name.setText(translate("Belum ada folder dipilih", language))
            self.lbl_folder_path.setText(translate("Pilih folder yang tersedia di PC.", language))

    def _autofill_display_name(self, path: str = ""):
        if self._display_name_user_edited:
            return
        folder_path = path or self.txt_folder.text().strip()
        if os.path.isdir(folder_path):
            self.txt_display_name.setText(Path(folder_path).name)

    def _autofill_new_folder_display_name(self, name: str):
        if not self._display_name_user_edited:
            self.txt_display_name.setText(name.strip())

    def _toggle_folder_mode(self):
        use_new = self.radio_existing.isChecked()
        self.radio_new.setChecked(use_new)
        self.radio_existing.setChecked(not use_new)
        self.existing_widget.setVisible(not use_new)
        self.new_widget.setVisible(use_new)
        language = self.property("_itshare_language") or "en"
        self.lbl_mode_prompt.setText(translate("Sudah punya folder?" if use_new else "Belum punya folder?", language))
        self.btn_folder_mode.setText(translate("Pilih folder yang sudah ada" if use_new else "Buat folder baru", language))

    def _set_duration(self, hours: int, custom: bool):
        if not custom:
            self.spin_timeout.setValue(hours)
        self.custom_duration_widget.setVisible(custom)

    @staticmethod
    def _set_access_card_selected(frame: QFrame, selected: bool):
        frame.setProperty("selected", selected)
        frame.style().unpolish(frame)
        frame.style().polish(frame)

    def _toggle_advanced(self, expanded: bool):
        self.advanced_widget.setVisible(expanded)
        self.advanced_toggle.setArrowType(Qt.ArrowType.UpArrow if expanded else Qt.ArrowType.DownArrow)

    def _update_advanced_summary(self, *_):
        if not hasattr(self, "combo_iface"):
            return
        ip = self.combo_iface.currentData() or "—"
        summary = f"Port {self.spin_port.value()} · Wi-Fi {ip} · Kata sandi otomatis"
        self.advanced_summary.setText(translate(summary, self.property("_itshare_language") or "en"))

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        self.lbl_pass.setEchoMode(QLineEdit.EchoMode.Normal if self._password_visible else QLineEdit.EchoMode.Password)
        language = self.property("_itshare_language") or "en"
        label = "Sembunyikan" if self._password_visible else "Tampilkan"
        self.btn_show_password.setText(translate(label, language))

    def _browse_folder(self):
        language = self.property("_itshare_language") or "en"
        path = QFileDialog.getExistingDirectory(self, translate("Pilih Folder", language), self.txt_folder.text().strip() or str(Path.home()))
        if path:
            self.txt_folder.setText(path)

    def _browse_parent(self):
        language = self.property("_itshare_language") or "en"
        path = QFileDialog.getExistingDirectory(self, translate("Pilih Direktori Induk", language), str(Path.home()))
        if path:
            self.txt_new_parent.setText(path)

    def _generate_credentials(self):
        self._username = generate_username()
        self._password = generate_password()
        self.lbl_user.setText(self._username)
        self.lbl_pass.setText(self._password)
        self._password_visible = False
        self.lbl_pass.setEchoMode(QLineEdit.EchoMode.Password)
        if hasattr(self, "btn_show_password"):
            language = self.property("_itshare_language") or "en"
            self.btn_show_password.setText(translate("Tampilkan", language))

    def _on_accept(self):
        import re
        language = self.property("_itshare_language") or "en"
        if self.radio_new.isChecked():
            name = self.txt_new_name.text().strip()
            parent = self.txt_new_parent.text().strip()
            if not name:
                QMessageBox.warning(self, translate("Nama Kosong", language), translate("Masukkan nama folder baru.", language))
                return
            folder = os.path.join(parent, name)
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, translate("Gagal Buat Folder", language), str(e))
                return
        else:
            folder = self.txt_folder.text().strip()
            if not folder or not os.path.isdir(folder):
                QMessageBox.warning(self, translate("Folder Tidak Valid", language), translate("Pilih folder yang valid.", language))
                return

        display_name = self.txt_display_name.text().strip() or Path(folder).name
        share_name = re.sub(r"[^A-Za-z0-9_$-]+", "_", display_name).strip("_-")[:80]
        if not share_name:
            share_name = "ItShare"
        if not re.fullmatch(r"[A-Za-z0-9_$-]{1,80}", share_name):
            QMessageBox.warning(self, translate("Nama Share Tidak Valid", language), translate("Gunakan 1–80 huruf, angka, garis bawah, tanda minus, atau $. Tanpa spasi.", language))
            return

        ip = self.combo_iface.currentData() or "127.0.0.1"
        self._session = ShareSession(
            folder_path=folder,
            username=self._username,
            password=self._password,
            port=self.spin_port.value(),
            read_only=self.chk_readonly.isChecked(),
            timeout_minutes=self.spin_timeout.value() * 60,
            share_name=share_name,
            host_ip=ip,
        )

        self._display_name = display_name
        self.accept()

    def get_session(self) -> Optional[ShareSession]:
        return self._session

    def get_display_name(self) -> str:
        return self._display_name

class itshareDialog(QDialog):
    """
    Share popup dialog:
    - Large QR code on left
    - Credentials panel on right
    - Copy buttons, Regenerate button
    """

    def __init__(self, session: ShareSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._qr_pixmap = QPixmap()
        self.setWindowTitle("QR Code — Hubungkan Perangkat")
        self.setMinimumSize(360, 380)
        self.setModal(True)
        screen = self.screen()
        available = screen.availableGeometry() if screen else None
        if available:
            self.resize(min(1000, int(available.width() * 0.86)), min(760, int(available.height() * 0.86)))
        else:
            self.resize(900, 680)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet("background:#ffffff; border-bottom:1px solid #dfe5df;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        lbl_h = QLabel("📱  Scan QR untuk Terhubung")
        lbl_h.setStyleSheet("color:#17211c; font-size:14px; font-weight:600;")
        h_lay.addWidget(lbl_h)
        h_lay.addStretch()
        lbl_folder = QLabel(Path(self.session.folder_path).name)
        lbl_folder.setStyleSheet("color:#68756e; font-size:12px;")
        h_lay.addWidget(lbl_folder)
        root.addWidget(header)

        body = QFrame()
        body.setStyleSheet("background:#f5f7f3;")
        body_lay = QHBoxLayout(body)
        self._body_layout = body_lay
        body_lay.setContentsMargins(24, 24, 24, 24)
        body_lay.setSpacing(24)

        qr_card = QFrame()
        qr_card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #dfe5df;
                border-radius: 10px;
            }
        """)
        qr_card_lay = QVBoxLayout(qr_card)
        self._qr_card_layout = qr_card_lay
        qr_card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_card_lay.setContentsMargins(16, 16, 16, 16)

        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        qr_card_lay.addWidget(self.lbl_qr)

        lbl_scan_hint = QLabel("Buka aplikasi SMB di HP → Scan QR ini")
        lbl_scan_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_scan_hint.setStyleSheet("font-size:11px; color:#86948b; margin-top:8px;")
        lbl_scan_hint.setWordWrap(True)
        qr_card_lay.addWidget(lbl_scan_hint)
        self._qr_card = qr_card

        body_lay.addWidget(qr_card)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        self._right_panel = QWidget()
        self._right_panel.setLayout(right_col)

        tab = QTabWidget()
        tab.setStyleSheet("""
            QTabWidget::pane { border:1px solid #dfe5df; border-radius:8px; background:#ffffff; top:-1px; }
            QTabBar::tab { background:#edf2f7; color:#4a5568; padding:8px 18px; margin-right:2px;
                           border-top-left-radius:6px; border-top-right-radius:6px;
                           font-weight:600; font-size:12px; }
            QTabBar::tab:selected { background:#ffffff; color:#176b49; border:1px solid #dfe5df; border-bottom:2px solid #176b49; }
        """)

        smb_tab = QWidget()
        smb_lay = QFormLayout(smb_tab)
        smb_lay.setContentsMargins(16, 14, 16, 14)
        smb_lay.setSpacing(10)

        def cred_row(label: str, value: str):
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet("font-family:'Courier New',monospace; font-size:12px; color:#1e293b; "
                                "background:#edf8f1; border:1px solid #dfe5df; border-radius:4px; padding:5px 8px;")
            lbl_v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            btn_copy = QPushButton("📋")
            btn_copy.setToolTip(f"Salin {label}")
            btn_copy.setFixedSize(30, 30)
            btn_copy.setStyleSheet("QPushButton{border:none;font-size:16px;} QPushButton:hover{background:#dfe5df;border-radius:4px;}")
            btn_copy.clicked.connect(lambda _, v=value: QGuiApplication.clipboard().setText(v))
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(4)
            row_lay.addWidget(lbl_v, stretch=1)
            row_lay.addWidget(btn_copy)
            smb_lay.addRow(f"<b>{label}</b>:", row_w)

        smb_path = f"\\\\{self.session.host_ip}\\{self.session.share_name}"
        cred_row("Alamat SMB", smb_path)
        cred_row("Username", self.session.username)
        cred_row("Password", self.session.password)
        cred_row("Port", str(self.session.port))

        mode_lbl = QLabel("Read-Only ✓" if self.session.read_only else "Baca & Tulis")
        mode_lbl.setStyleSheet(
            "color: #2c9968; font-weight:600;" if self.session.read_only
            else "color: #f59e0b; font-weight:600;"
        )
        smb_lay.addRow("<b>Mode:</b>", mode_lbl)

        tab.addTab(smb_tab, "🔗 Koneksi SMB")
        right_col.addWidget(tab)

        all_info = (
            f"SMB Path: {smb_path}\n"
            f"Username: {self.session.username}\n"
            f"Password: {self.session.password}\n"
            f"Port: {self.session.port}\n"
            f"Mode: {'Read-Only' if self.session.read_only else 'Baca-Tulis'}"
        )
        btn_copy_all = QPushButton("📋  Salin Semua Kredensial")
        btn_copy_all.setStyleSheet(BTN_NORMAL)
        btn_copy_all.clicked.connect(lambda: QGuiApplication.clipboard().setText(all_info))
        right_col.addWidget(btn_copy_all)

        btn_wifi = QPushButton("📶  Tampilkan QR WiFi")
        btn_wifi.setStyleSheet(BTN_NORMAL)
        btn_wifi.clicked.connect(self._open_wifi)
        right_col.addWidget(btn_wifi)

        btn_save_qr = QPushButton("Simpan QR...")
        btn_save_qr.setStyleSheet(BTN_NORMAL)
        btn_save_qr.clicked.connect(self._save_qr)
        right_col.addWidget(btn_save_qr)

        right_col.addStretch()

        if self.session.timeout_minutes > 0:
            self.lbl_countdown = QLabel()
            self.lbl_countdown.setStyleSheet("font-size:12px; color:#f59e0b; font-weight:600;")
            right_col.addWidget(self.lbl_countdown)
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(1000)
            self._tick()
        else:
            lbl_perm = QLabel("⏱ Sesi Permanen")
            lbl_perm.setStyleSheet("font-size:12px; color:#86948b;")
            right_col.addWidget(lbl_perm)

        body_lay.addWidget(self._right_panel, stretch=1)
        self._body_scroll = QScrollArea(self)
        self._body_scroll.setWidgetResizable(True)
        self._body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._body_scroll.setWidget(body)
        root.addWidget(self._body_scroll, stretch=1)

        footer = QFrame()
        footer.setFixedHeight(52)
        footer.setStyleSheet("background:#ffffff; border-top:1px solid #dfe5df;")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(20, 0, 20, 0)
        lbl_info = QLabel(f"📂 {self.session.folder_path}")
        lbl_info.setStyleSheet("color:#86948b; font-size:11px;")
        foot_lay.addWidget(lbl_info)
        foot_lay.addStretch()
        btn_close = QPushButton("Tutup")
        btn_close.setStyleSheet(BTN_NORMAL)
        btn_close.clicked.connect(self.accept)
        foot_lay.addWidget(btn_close)
        root.addWidget(footer)

        self._render_qr()
        self._resize_qr_content()

    def _render_qr(self):
        try:
            payload = build_smb_payload(self.session)
            import json
            pixmap = render_to_pixmap(json.dumps(payload), box_size=14)
            self._qr_pixmap = pixmap
            self._resize_qr_content()
        except Exception as e:
            self._qr_pixmap = QPixmap()
            self.lbl_qr.setText(f"⚠️ QR error:\n{e}")

    def _save_qr(self):
        if self._qr_pixmap.isNull():
            QMessageBox.warning(self, "QR belum tersedia", "QR SMB belum berhasil dibuat.")
            return
        default_name = f"ItShare-SMB-{Path(self.session.folder_path).name or 'share'}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Simpan QR SMB", default_name, "PNG Image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if not self._qr_pixmap.save(path, "PNG"):
            QMessageBox.critical(self, "Gagal menyimpan QR", "Gambar QR tidak dapat disimpan ke lokasi tersebut.")

    def _resize_qr_content(self):
        if not hasattr(self, "_body_layout"):
            return
        width = max(1, self.width())
        height = max(1, self.height())
        narrow = width < 760
        self._body_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )
        margins = 12 if narrow else 24
        self._body_layout.setContentsMargins(margins, margins, margins, margins)
        self._body_layout.setSpacing(12 if narrow else 24)
        width_limit = width - (64 if narrow else 100)
        height_limit = height - (300 if narrow else 200)
        qr_size = max(160, min(400, width_limit if narrow else width_limit // 2, height_limit))
        self.lbl_qr.setFixedSize(qr_size, qr_size)
        if not self._qr_pixmap.isNull():
            self.lbl_qr.setPixmap(self._qr_pixmap.scaled(
                qr_size, qr_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_qr_content()

    def _open_wifi(self):
        dlg = WifiQrDialog(parent=self)
        dlg.exec()

    def _tick(self):
        if hasattr(self, '_timer') and self.session.is_expired:
            self._timer.stop()
            self.lbl_countdown.setText("⏱ Sesi telah berakhir")
            return
        rem = self.session.remaining_seconds
        m, s = divmod(rem, 60)
        self.lbl_countdown.setText(f"⏱ Sisa waktu: {m:02d}:{s:02d}")

class WifiQrDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR Code — Sambung WiFi")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._qr_pixmap = QPixmap()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("📶  Bagikan Koneksi WiFi via QR")
        lbl_title.setStyleSheet("font-size:15px; font-weight:700; color:#1e293b;")
        layout.addWidget(lbl_title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#dfe5df; max-height:1px;")
        layout.addWidget(sep)

        ssid = get_wifi_ssid() or ""
        form = QFormLayout()
        form.setSpacing(10)

        self.txt_ssid = QLineEdit(ssid)
        self.txt_ssid.setPlaceholderText("Nama WiFi (SSID)...")
        form.addRow("SSID:", self.txt_ssid)

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Password WiFi...")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.txt_pass)

        self.combo_sec = QComboBox()
        self.combo_sec.addItems(["WPA", "WEP", "nopass"])
        form.addRow("Keamanan:", self.combo_sec)

        self.chk_hidden = QCheckBox("Jaringan tersembunyi")
        form.addRow(self.chk_hidden)

        layout.addLayout(form)

        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setMinimumHeight(200)
        self.lbl_qr.setStyleSheet("""
            background: #ffffff;
            border: 1px solid #dfe5df;
            border-radius: 8px;
        """)
        layout.addWidget(self.lbl_qr)

        btn_row = QHBoxLayout()
        btn_gen = QPushButton("📱  Generate QR")
        btn_gen.setStyleSheet(BTN_PRIMARY)
        btn_gen.clicked.connect(self._render)
        self.btn_save_qr = QPushButton("Simpan QR...")
        self.btn_save_qr.setStyleSheet(BTN_NORMAL)
        self.btn_save_qr.setEnabled(False)
        self.btn_save_qr.clicked.connect(self._save_qr)
        btn_close = QPushButton("Tutup")
        btn_close.setStyleSheet(BTN_NORMAL)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_gen)
        btn_row.addWidget(self.btn_save_qr)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        if ssid:
            self._render()

    def _render(self):
        ssid = self.txt_ssid.text().strip()
        password = self.txt_pass.text()
        security = self.combo_sec.currentText()
        hidden = self.chk_hidden.isChecked()
        if not ssid:
            self.lbl_qr.setText("⚠️ Masukkan SSID terlebih dahulu")
            return
        try:
            payload = build_wifi_payload(ssid, security, password, hidden)
            pixmap = render_to_pixmap(payload)
            self._qr_pixmap = pixmap
            self.lbl_qr.setPixmap(pixmap.scaled(200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            self.btn_save_qr.setEnabled(True)
        except Exception as e:
            self._qr_pixmap = QPixmap()
            self.btn_save_qr.setEnabled(False)
            self.lbl_qr.setText(f"⚠️ Error: {e}")

    def _save_qr(self):
        if self._qr_pixmap.isNull():
            QMessageBox.warning(self, "QR belum tersedia", "Buat QR Wi-Fi terlebih dahulu.")
            return
        ssid = self.txt_ssid.text().strip()
        safe_ssid = "".join(ch for ch in ssid if ch.isalnum() or ch in "-_ ").strip() or "WiFi"
        path, _ = QFileDialog.getSaveFileName(self, "Simpan QR Wi-Fi", f"ItShare-WiFi-{safe_ssid}.png", "PNG Image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if not self._qr_pixmap.save(path, "PNG"):
            QMessageBox.critical(self, "Gagal menyimpan QR", "Gambar QR tidak dapat disimpan ke lokasi tersebut.")

