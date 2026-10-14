"""
ui/tab_setup.py - Modernized Tab Setup widget for ItShare.
Features:
- Visual folder selector with segmented choice and enhanced drag & drop zone
- Settings grouped in clean card layouts with informative hints
- Live countdown & status banner with badges
- High-visibility QR code display with copyable credentials and quick actions
- Independent WiFi dialog
- Folder history list with instant select, backup & import tools
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Tuple

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QRadioButton, QButtonGroup,
    QCheckBox, QSpinBox, QComboBox, QFileDialog, QMessageBox,
    QListWidget, QGroupBox, QDialog, QDialogButtonBox, QFrame,
    QScrollArea
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor

from core.session import ShareSession
from core.credentials import generate_username, generate_password
from core.qr_generator import build_smb_payload, build_wifi_payload, render_to_pixmap
from core.network import get_local_ips, get_wifi_ssid
from core.history import HistoryManager
from core.smb_server import SMBServerManager
from ui.styles import BTN_PRIMARY, BTN_DANGER, BTN_NORMAL

logger = logging.getLogger(__name__)

class DropAreaWidget(QFrame):
    folder_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            DropAreaWidget {
                border: 2px dashed #86948b;
                border-radius: 10px;
                background-color: #edf8f1;
                min-height: 80px;
            }
            DropAreaWidget:hover {
                border-color: #176b49;
                background-color: #dff3e8;
            }
        """)
        layout = QVBoxLayout(self)
        self.icon_label = QLabel("📂")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 24px;")

        self.label = QLabel("Tarik & Lepas Folder ke Sini atau Gunakan Tombol Jelajahi")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #52635a; font-weight: 500; font-size: 13px;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and os.path.isdir(urls[0].toLocalFile()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.folder_dropped.emit(path)
                event.acceptProposedAction()
            else:
                QMessageBox.warning(
                    self,
                    "Peringatan Folder",
                    "Hanya folder/direktori yang dapat dibagikan. File tunggal tidak didukung."
                )

class WiFiDialog(QDialog):
    """Dialog terpisah untuk menampilkan QR WiFi dengan escape karakter aman."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Koneksi WiFi - QR Code")
        self.resize(380, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        desc = QLabel("Pindai QR ini dari kamera ponsel untuk terhubung otomatis ke WiFi:")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #52635a;")
        layout.addWidget(desc)

        detected_ssid = get_wifi_ssid() or ""

        form_card = QFrame()
        form_card.setStyleSheet("background-color: #edf8f1; border: 1px solid #dfe5df; border-radius: 8px; padding: 10px;")
        form_layout = QGridLayout(form_card)

        form_layout.addWidget(QLabel("Nama SSID:"), 0, 0)
        self.input_ssid = QLineEdit(detected_ssid)
        self.input_ssid.setPlaceholderText("Nama jaringan WiFi")
        form_layout.addWidget(self.input_ssid, 0, 1)

        form_layout.addWidget(QLabel("Keamanan:"), 1, 0)
        self.combo_sec = QComboBox()
        self.combo_sec.addItems(["WPA", "WEP", "NOPASS"])
        form_layout.addWidget(self.combo_sec, 1, 1)

        form_layout.addWidget(QLabel("Password:"), 2, 0)
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.setPlaceholderText("Password WiFi...")
        form_layout.addWidget(self.input_pass, 2, 1)

        layout.addWidget(form_card)

        self.btn_generate = QPushButton("🔄 Perbarui QR WiFi")
        self.btn_generate.clicked.connect(self.update_qr)
        layout.addWidget(self.btn_generate)

        self.lbl_qr = QLabel("Masukkan detail lalu klik Perbarui QR WiFi")
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setStyleSheet("background-color: white; border: 1px solid #cad5cd; border-radius: 8px; padding: 10px;")
        self.lbl_qr.setMinimumSize(240, 240)
        layout.addWidget(self.lbl_qr)

        if detected_ssid:
            self.update_qr()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_qr(self):
        ssid = self.input_ssid.text().strip()
        if not ssid:
            QMessageBox.warning(self, "Peringatan", "SSID WiFi tidak boleh kosong.")
            return

        sec = self.combo_sec.currentText()
        pwd = self.input_pass.text()
        payload = build_wifi_payload(ssid=ssid, security=sec, password=pwd)

        pixmap = render_to_pixmap(payload, box_size=6)
        self.lbl_qr.setPixmap(pixmap.scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio))

class TabSetup(QWidget):
    session_started = Signal(object)
    session_stopped = Signal()

    def __init__(self, smb_manager: SMBServerManager, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.smb_manager = smb_manager
        self.history_manager = history_manager

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._on_tick)

        self.init_ui()
        self.load_history_list()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        left_content = QWidget()
        left_box = QVBoxLayout(left_content)
        left_box.setContentsMargins(0, 0, 8, 0)
        left_box.setSpacing(14)

        grp_folder = QGroupBox("📁 1. Pilih Folder yang Dibagikan")
        folder_layout = QVBoxLayout(grp_folder)
        folder_layout.setSpacing(10)

        radio_layout = QHBoxLayout()
        self.radio_existing = QRadioButton("Folder yang Sudah Ada")
        self.radio_new = QRadioButton("Buat Folder Baru")
        self.radio_existing.setChecked(True)
        radio_group = QButtonGroup(self)
        radio_group.addButton(self.radio_existing)
        radio_group.addButton(self.radio_new)
        radio_layout.addWidget(self.radio_existing)
        radio_layout.addWidget(self.radio_new)
        folder_layout.addLayout(radio_layout)

        self.existing_widget = QWidget()
        exist_layout = QHBoxLayout(self.existing_widget)
        exist_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_folder_path = QLineEdit()
        self.txt_folder_path.setPlaceholderText("Pilih direktori melalui tombol Jelajahi...")
        self.btn_browse = QPushButton("📂 Jelajahi...")
        self.btn_browse.clicked.connect(self._on_browse_existing)
        exist_layout.addWidget(self.txt_folder_path)
        exist_layout.addWidget(self.btn_browse)
        folder_layout.addWidget(self.existing_widget)

        self.new_folder_widget = QWidget()
        new_layout = QGridLayout(self.new_folder_widget)
        new_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_parent_dir = QLineEdit()
        self.txt_parent_dir.setPlaceholderText("Direktori Induk (Parent Folder)...")
        self.btn_browse_parent = QPushButton("Pilih Induk...")
        self.btn_browse_parent.clicked.connect(self._on_browse_parent)
        self.txt_new_folder_name = QLineEdit()
        self.txt_new_folder_name.setPlaceholderText("Nama Folder Baru (misal: BerkasShare)")
        new_layout.addWidget(QLabel("Induk:"), 0, 0)
        new_layout.addWidget(self.txt_parent_dir, 0, 1)
        new_layout.addWidget(self.btn_browse_parent, 0, 2)
        new_layout.addWidget(QLabel("Nama:"), 1, 0)
        new_layout.addWidget(self.txt_new_folder_name, 1, 1, 1, 2)
        self.new_folder_widget.setVisible(False)
        folder_layout.addWidget(self.new_folder_widget)

        self.radio_existing.toggled.connect(self._on_radio_mode_changed)

        self.drop_area = DropAreaWidget()
        self.drop_area.folder_dropped.connect(self._on_folder_dropped)
        folder_layout.addWidget(self.drop_area)

        left_box.addWidget(grp_folder)

        grp_options = QGroupBox("⚙️ 2. Pengaturan Berbagi & Keamanan")
        opt_grid = QGridLayout(grp_options)
        opt_grid.setVerticalSpacing(10)
        opt_grid.setHorizontalSpacing(12)

        self.chk_readonly = QCheckBox("Mode Hanya-Baca (Read-Only) [Direkomendasikan]")
        self.chk_readonly.setChecked(True)
        self.chk_readonly.setStyleSheet("font-weight: 600; color: #047857;")
        opt_grid.addWidget(self.chk_readonly, 0, 0, 1, 2)

        opt_grid.addWidget(QLabel("Batas Waktu:"), 1, 0)
        time_box = QHBoxLayout()
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(0, 1440)
        self.spin_timeout.setValue(0)
        time_box.addWidget(self.spin_timeout)
        time_box.addWidget(QLabel("Menit (0 = Permanen)"))
        opt_grid.addLayout(time_box, 1, 1)

        opt_grid.addWidget(QLabel("Port SMB Server:"), 2, 0)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(4455)
        opt_grid.addWidget(self.spin_port, 2, 1)

        opt_grid.addWidget(QLabel("Interface Jaringan:"), 3, 0)
        self.combo_ip = QComboBox()
        self._populate_ip_combo()
        opt_grid.addWidget(self.combo_ip, 3, 1)

        left_box.addWidget(grp_options)

        btn_action_layout = QHBoxLayout()
        self.btn_start = QPushButton("Buat Share && Mulai Server")
        self.btn_start.setStyleSheet(BTN_PRIMARY)
        self.btn_start.clicked.connect(self.on_start_share)

        self.btn_stop = QPushButton("Hentikan Server")
        self.btn_stop.setStyleSheet(BTN_DANGER)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop_share)

        btn_action_layout.addWidget(self.btn_start, stretch=2)
        btn_action_layout.addWidget(self.btn_stop, stretch=1)
        left_box.addLayout(btn_action_layout)

        self.status_card = QFrame()
        self.status_card.setStyleSheet("""
            QFrame {
                background-color: #edf3ef;
                border: 1px solid #cad5cd;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        stat_layout = QHBoxLayout(self.status_card)
        stat_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QLabel("Status: Server belum berjalan")
        self.lbl_status.setStyleSheet("font-weight: 600; color: #52635a; font-size: 13px;")
        stat_layout.addWidget(self.lbl_status)
        left_box.addWidget(self.status_card)

        sub_action_layout = QHBoxLayout()
        self.btn_wifi_dialog = QPushButton("📶 Buka QR WiFi...")
        self.btn_wifi_dialog.clicked.connect(self._open_wifi_dialog)
        self.btn_regenerate = QPushButton("🔄 Regenerasi Kredensial")
        self.btn_regenerate.setEnabled(False)
        self.btn_regenerate.clicked.connect(self.on_regenerate)
        sub_action_layout.addWidget(self.btn_wifi_dialog)
        sub_action_layout.addWidget(self.btn_regenerate)
        left_box.addLayout(sub_action_layout)

        grp_history = QGroupBox("📜 Riwayat Folder")
        hist_layout = QVBoxLayout(grp_history)
        hist_layout.setSpacing(8)
        self.list_history = QListWidget()
        self.list_history.setToolTip("Klik dua kali folder untuk memilih ulang")
        self.list_history.itemDoubleClicked.connect(self._on_history_double_clicked)
        hist_layout.addWidget(self.list_history)

        hist_btn_layout = QHBoxLayout()
        self.btn_backup = QPushButton("💾 Backup Riwayat...")
        self.btn_backup.clicked.connect(self._on_export_backup)
        self.btn_import = QPushButton("📂 Import Riwayat...")
        self.btn_import.clicked.connect(self._on_import_backup)
        hist_btn_layout.addWidget(self.btn_backup)
        hist_btn_layout.addWidget(self.btn_import)
        hist_layout.addLayout(hist_btn_layout)

        left_box.addWidget(grp_history)

        scroll.setWidget(left_content)
        main_layout.addWidget(scroll, stretch=3)

        right_card = QFrame()
        right_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dfe5df;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        right_box = QVBoxLayout(right_card)
        right_box.setSpacing(12)

        lbl_qr_title = QLabel("📲 Kode QR SMB (Ponsel Host)")
        lbl_qr_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #1e293b;")
        right_box.addWidget(lbl_qr_title)

        lbl_qr_desc = QLabel("Pindai QR ini melalui aplikasi ItShare di Android/iOS untuk langsung membuka file.")
        lbl_qr_desc.setWordWrap(True)
        lbl_qr_desc.setStyleSheet("font-size: 12px; color: #68756e;")
        right_box.addWidget(lbl_qr_desc)

        self.lbl_qr_display = QLabel("Belum ada sesi aktif.\nPilih folder lalu klik 'Buat Share & Mulai Server'.")
        self.lbl_qr_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr_display.setMinimumSize(320, 320)
        self.lbl_qr_display.setStyleSheet("""
            QLabel {
                background-color: #edf8f1;
                border: 2px dashed #cad5cd;
                color: #68756e;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        right_box.addWidget(self.lbl_qr_display)

        self.creds_box = QFrame()
        self.creds_box.setStyleSheet("""
            QFrame {
                background-color: #edf3ef;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        creds_layout = QVBoxLayout(self.creds_box)
        creds_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_creds_info = QLabel("Kredensial akan digenerate otomatis saat sesi dibuat.")
        self.lbl_creds_info.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_creds_info.setStyleSheet("color: #304037; font-size: 12px;")
        creds_layout.addWidget(self.lbl_creds_info)
        right_box.addWidget(self.creds_box)

        right_box.addStretch()
        main_layout.addWidget(right_card, stretch=2)

    def _populate_ip_combo(self):
        self.combo_ip.clear()
        ips = get_local_ips()
        for label, ip in ips:
            self.combo_ip.addItem(f"{label} ({ip})", ip)

    def _on_radio_mode_changed(self, checked):
        if self.radio_existing.isChecked():
            self.existing_widget.setVisible(True)
            self.drop_area.setVisible(True)
            self.new_folder_widget.setVisible(False)
        else:
            self.existing_widget.setVisible(False)
            self.drop_area.setVisible(False)
            self.new_folder_widget.setVisible(True)

    def _on_browse_existing(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder untuk Dibagikan")
        if folder:
            self.txt_folder_path.setText(os.path.normpath(folder))

    def _on_browse_parent(self):
        parent = QFileDialog.getExistingDirectory(self, "Pilih Direktori Induk")
        if parent:
            self.txt_parent_dir.setText(os.path.normpath(parent))

    def _on_folder_dropped(self, folder_path: str):
        self.radio_existing.setChecked(True)
        self.txt_folder_path.setText(os.path.normpath(folder_path))

    def _open_wifi_dialog(self):
        dlg = WiFiDialog(self)
        dlg.exec()

    def _on_history_double_clicked(self, item):
        self.radio_existing.setChecked(True)
        self.txt_folder_path.setText(item.text())

    def load_history_list(self):
        self.list_history.clear()
        for f in self.history_manager.get_recent_folders():
            self.list_history.addItem(f)

    def _on_export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Cadangan Riwayat", "itshare_backup.json", "JSON Files (*.json)")
        if path:
            self.history_manager.export_backup(path)
            QMessageBox.information(self, "Cadangan", "Riwayat dan pengaturan berhasil diekspor.")

    def _on_import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pilih File Cadangan", "", "JSON Files (*.json)")
        if path:
            res = self.history_manager.import_backup(path)
            if res.success:
                self.load_history_list()
                QMessageBox.information(self, "Impor Berhasil", res.message)
            else:
                QMessageBox.critical(self, "Impor Gagal", res.error or "Gagal memproses file cadangan.")

    def _validate_path(self, path_str: str) -> bool:
        if not path_str or ".." in path_str:
            return False
        norm = os.path.normpath(path_str)
        return os.path.exists(norm) and os.path.isdir(norm)

    def on_start_share(self):
        if self.radio_existing.isChecked():
            folder = self.txt_folder_path.text().strip()
            if not self._validate_path(folder):
                QMessageBox.warning(self, "Path Tidak Valid", "Silakan pilih direktori yang valid dan dapat diakses.")
                return
        else:
            parent = self.txt_parent_dir.text().strip()
            name = self.txt_new_folder_name.text().strip()
            if not parent or not os.path.isdir(parent) or not name:
                QMessageBox.warning(self, "Input Kurang", "Tentukan direktori induk dan nama folder baru.")
                return
            if any(char in name for char in '<>:"/\\|?*'):
                QMessageBox.warning(self, "Nama Tidak Valid", "Nama folder mengandung karakter yang tidak diizinkan.")
                return
            folder = os.path.normpath(os.path.join(parent, name))
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Gagal Membuat Folder", f"Tidak dapat membuat folder: {e}")
                return

        read_only = self.chk_readonly.isChecked()
        if not read_only:
            ans = QMessageBox.warning(
                self,
                "Konfirmasi Akses Tulis (Read-Write)",
                "Anda menonaktifkan Read-Only. Perangkat HP/klien dapat mengunggah dan menghapus file di folder ini.\n\nLanjutkan?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        username = generate_username(8)
        password = generate_password(16)
        port = self.spin_port.value()
        timeout_m = self.spin_timeout.value()
        host_ip = self.combo_ip.currentData() or "127.0.0.1"

        session = ShareSession(
            folder_path=folder,
            username=username,
            password=password,
            port=port,
            read_only=read_only,
            timeout_minutes=timeout_m,
            host_ip=host_ip
        )

        self.lbl_status.setText("Status: Memulai server SMB...")
        success, msg = self.smb_manager.start(session)
        if not success:
            self.lbl_status.setText(f"Status Error: {msg}")
            QMessageBox.critical(self, "Server SMB Gagal", msg)
            return

        self.history_manager.add_folder(folder)
        self.load_history_list()

        self._render_active_qr(session)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_regenerate.setEnabled(True)

        if timeout_m > 0:
            self.countdown_timer.start()

        self.status_card.setStyleSheet("""
            QFrame {
                background-color: #ecfdf5;
                border: 1px solid #2c9968;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        self.lbl_status.setText(f"✅ Server Aktif di {host_ip}:{port}")
        self.lbl_status.setStyleSheet("font-weight: 700; color: #065f46; font-size: 13px;")
        self.session_started.emit(session)

    def _render_active_qr(self, session: ShareSession):
        payload = build_smb_payload(session)
        payload_str = json.dumps(payload, separators=(',', ':'))
        pixmap = render_to_pixmap(payload_str, box_size=8)
        self.lbl_qr_display.setStyleSheet("background-color: white; border: 1px solid #dfe5df; border-radius: 12px; padding: 12px;")
        self.lbl_qr_display.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio))

        exp_text = "Permanen" if session.timeout_minutes == 0 else f"{session.timeout_minutes} Menit"
        mode_text = "🔒 Read-Only" if session.read_only else "✏️ Read-Write"
        self.lbl_creds_info.setText(
            f"<b>Pengguna:</b> <code>{session.username}</code><br>"
            f"<b>Port:</b> <code>{session.port}</code> | <b>Mode:</b> {mode_text}<br>"
            f"<b>Batas Waktu:</b> {exp_text}"
        )

    def _on_tick(self):
        session = self.smb_manager.active_session
        if not session or session.timeout_minutes <= 0:
            self.countdown_timer.stop()
            return

        rem = session.remaining_seconds
        if rem <= 0:
            self.countdown_timer.stop()
            self.on_stop_share()
            QMessageBox.information(self, "Sesi Berakhir", "Batas waktu sesi berbagi telah habis. Server SMB dihentikan.")
        else:
            mins, secs = divmod(rem, 60)
            self.lbl_status.setText(f"✅ Server Aktif (Sisa Waktu: {mins:02d}:{secs:02d})")

    def on_stop_share(self):
        self.countdown_timer.stop()
        self.smb_manager.stop()
        self.status_card.setStyleSheet("""
            QFrame {
                background-color: #edf3ef;
                border: 1px solid #cad5cd;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        self.lbl_status.setText("Status: Server dihentikan.")
        self.lbl_status.setStyleSheet("font-weight: 600; color: #52635a; font-size: 13px;")

        self.lbl_qr_display.clear()
        self.lbl_qr_display.setStyleSheet("""
            QLabel {
                background-color: #edf8f1;
                border: 2px dashed #cad5cd;
                color: #68756e;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        self.lbl_qr_display.setText("Sesi dihentikan.\nPilih folder lalu klik 'Buat Share & Mulai Server'.")
        self.lbl_creds_info.setText("Kredensial akan digenerate otomatis saat sesi dibuat.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_regenerate.setEnabled(False)
        self.session_stopped.emit()

    def on_regenerate(self):
        session = self.smb_manager.active_session
        if not session or not self.smb_manager.is_running():
            return

        session.username = generate_username(8)
        session.password = generate_password(16)
        success, msg = self.smb_manager.start(session)
        if success:
            self._render_active_qr(session)
            QMessageBox.information(self, "Regenerasi Berhasil", "Kredensial dan QR baru telah dibuat. Ponsel/klien lama terputus.")
        else:
            QMessageBox.critical(self, "Gagal Restart", msg)
