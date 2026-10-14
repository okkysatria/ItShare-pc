"""Connection and transfer activity for the ItShare desktop app."""
from datetime import datetime
from pathlib import PureWindowsPath

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QMessageBox,
)

from core.history import HistoryManager
from ui.styles import BTN_NORMAL, BTN_DANGER
from ui.i18n import apply_language
from ui.styles import apply_theme

class PageHistory(QWidget):
    def __init__(self, history_manager: HistoryManager, smb_manager=None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.smb_manager = smb_manager
        self._view = "connections"
        self._current_page = 0
        self._page_size = 20
        self._client_snapshot = None
        self._client_timer = QTimer(self)
        self._client_timer.setInterval(3000)
        self._client_timer.timeout.connect(self._refresh_clients)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        heading = QVBoxLayout()
        heading.setSpacing(5)
        eyebrow = QLabel("AKTIVITAS")
        eyebrow.setStyleSheet("color:#176b49; font-size:10px; font-weight:700; letter-spacing:1px;")
        title = QLabel("Riwayat")
        title.setStyleSheet("color:#17211c; font-size:26px; font-weight:700;")
        heading.addWidget(eyebrow)
        heading.addWidget(title)
        root.addLayout(heading)

        controls = QHBoxLayout()
        self.btn_connections = QPushButton("Koneksi")
        self.btn_connections.setCheckable(True)
        self.btn_connections.clicked.connect(lambda: self._select_view("connections"))
        self.btn_connections.setStyleSheet("QPushButton { background:#f3f7f4; border:1px solid #dfe8e1; border-radius:10px; padding:8px 16px; } QPushButton:checked { background:#176b49; color:white; border-color:#176b49; }")
        self.btn_transfers = QPushButton("Transfer Berkas")
        self.btn_transfers.setCheckable(True)
        self.btn_transfers.clicked.connect(lambda: self._select_view("transfers"))
        self.btn_transfers.setStyleSheet("QPushButton { background:#f3f7f4; border:1px solid #dfe8e1; border-radius:10px; padding:8px 16px; } QPushButton:checked { background:#176b49; color:white; border-color:#176b49; }")
        self.btn_clients = QPushButton("Klien Aktif")
        self.btn_clients.setCheckable(True)
        self.btn_clients.setStyleSheet("QPushButton { background:#f3f7f4; border:1px solid #dfe8e1; border-radius:10px; padding:8px 16px; } QPushButton:checked { background:#176b49; color:white; border-color:#176b49; }")
        self.btn_clients.clicked.connect(lambda: self._select_view("clients"))
        self.btn_refresh = QPushButton("Muat Ulang")
        self.btn_refresh.setStyleSheet(BTN_NORMAL)
        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_clear = QPushButton("Hapus Koneksi")
        self.btn_clear.setStyleSheet(BTN_DANGER)
        self.btn_clear.clicked.connect(self._clear_current_history)
        controls.addWidget(self.btn_connections)
        controls.addWidget(self.btn_transfers)
        controls.addWidget(self.btn_clients)
        controls.addStretch()
        controls.addWidget(self.btn_refresh)
        controls.addWidget(self.btn_clear)
        root.addLayout(controls)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setStyleSheet("""
            QListWidget { background:transparent; border:0; outline:0; }
            QListWidget::item { background:#ffffff; border:1px solid #dfe8e1; border-radius:12px; }
            QListWidget::item:hover { background:#f9fcfa; }
            QListWidget::item:selected { background:#e7f4ec; color:#17211c; }
        """)
        root.addWidget(self.list_widget, 1)

        self.pagination = QWidget()
        page_layout = QHBoxLayout(self.pagination)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_prev_page = QPushButton("‹ Sebelumnya")
        self.btn_prev_page.setStyleSheet(BTN_NORMAL)
        self.btn_prev_page.clicked.connect(lambda: self._change_page(-1))
        self.lbl_page = QLabel("")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setStyleSheet("color:#68756e; font-size:11px;")
        self.btn_next_page = QPushButton("Berikutnya ›")
        self.btn_next_page.setStyleSheet(BTN_NORMAL)
        self.btn_next_page.clicked.connect(lambda: self._change_page(1))
        page_layout.addWidget(self.btn_prev_page)
        page_layout.addStretch()
        page_layout.addWidget(self.lbl_page)
        page_layout.addStretch()
        page_layout.addWidget(self.btn_next_page)
        self.pagination.setVisible(False)
        root.addWidget(self.pagination)
        self._select_view("connections")

    def _select_view(self, view: str):
        self._view = view
        self._current_page = 0
        self.btn_connections.setChecked(view == "connections")
        self.btn_transfers.setChecked(view == "transfers")
        self.btn_clients.setChecked(view == "clients")
        if view == "clients":
            self._client_snapshot = None
            self._client_timer.start()
        else:
            self._client_timer.stop()
        has_items = bool(
            self.history_manager.get_transfer_history() if view == "transfers"
            else self.history_manager.get_connection_history() if view == "connections"
            else False
        )
        self.btn_clear.setEnabled(has_items)
        self.btn_clear.setText("Hapus Riwayat Transfer" if view == "transfers" else "Hapus Koneksi")
        self._refresh()

    def _refresh(self):
        self.list_widget.clear()
        if self._view == "clients":
            self._client_snapshot = None
            self._refresh_clients(force=True)
            return
        if self._view == "transfers":
            items = self.history_manager.get_transfer_history()
            if not items:
                self.pagination.setVisible(False)
                self.btn_clear.setEnabled(False)
                self._add_empty_state("Belum ada aktivitas transfer di PC", "")
                self._apply_page_language()
                return
            page_count = max(1, (len(items) + self._page_size - 1) // self._page_size)
            self._current_page = max(0, min(self._current_page, page_count - 1))
            start = self._current_page * self._page_size
            for event in items[start:start + self._page_size]:
                self._add_transfer_item(event)
            self.pagination.setVisible(page_count > 1)
            self.lbl_page.setText(f"Halaman {self._current_page + 1} dari {page_count} · {len(items)} berkas")
            self.btn_prev_page.setEnabled(self._current_page > 0)
            self.btn_next_page.setEnabled(self._current_page < page_count - 1)
            self.btn_clear.setEnabled(True)
            self._apply_page_language()
            return

        items = self.history_manager.get_connection_history()
        if not items:
            self.pagination.setVisible(False)
            self._add_empty_state(
                "Belum ada riwayat koneksi",
                "",
            )
            self.btn_clear.setEnabled(False)
            self._apply_page_language()
            return

        self.btn_clear.setEnabled(True)
        page_count = max(1, (len(items) + self._page_size - 1) // self._page_size)
        self._current_page = max(0, min(self._current_page, page_count - 1))
        start = self._current_page * self._page_size
        for event in items[start:start + self._page_size]:
            self._add_connection_item(event)
        self.pagination.setVisible(page_count > 1)
        self.lbl_page.setText(f"Halaman {self._current_page + 1} dari {page_count} · {len(items)} sesi")
        self.btn_prev_page.setEnabled(self._current_page > 0)
        self.btn_next_page.setEnabled(self._current_page < page_count - 1)
        self._apply_page_language()

    def _apply_page_language(self):
        top_level = self.window()
        language = top_level.property("_itshare_language") or "en"
        theme = top_level.property("_itshare_theme") or "system"
        apply_theme(self, theme)
        apply_language(self, language)

    def _change_page(self, delta: int):
        self._current_page += delta
        self._refresh()

    def refresh(self):
        """Public refresh hook used when a server session starts or stops."""
        if self._view == "clients":
            self._refresh_clients(force=True)
        else:
            self._refresh()

    def _refresh_clients(self, force: bool = False):
        clients = self.smb_manager.get_connected_clients() if self.smb_manager else []
        snapshot = tuple((client["address"], client["connections"]) for client in clients)
        if not force and snapshot == self._client_snapshot:
            return
        self._client_snapshot = snapshot
        self.list_widget.clear()
        self.pagination.setVisible(False)
        self.btn_clear.setEnabled(False)
        if not clients:
            self._add_empty_state("Belum ada klien aktif", "")
        else:
            for client in clients:
                self._add_client_item(client)
        self._apply_page_language()

    def _add_client_item(self, client: dict):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 76))
        self.list_widget.addItem(item)
        row = QFrame()
        row.setStyleSheet("QFrame { background:#ffffff; border:1px solid #dfe8e1; border-radius:12px; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)
        badge = QLabel("TERSAMBUNG")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("color:#176b49; background:#e7f4ec; border:0; border-radius:9px; padding:6px 9px; font-size:9px; font-weight:700;")
        layout.addWidget(badge)
        details = QVBoxLayout()
        address = QLabel(client["address"])
        address.setStyleSheet("color:#17211c; font-size:13px; font-weight:600; border:0;")
        count = int(client.get("connections", 1))
        subtitle = QLabel(f"{count} koneksi SMB")
        subtitle.setStyleSheet("color:#68756e; font-size:11px; border:0;")
        details.addWidget(address)
        details.addWidget(subtitle)
        layout.addLayout(details, 1)
        self.list_widget.setItemWidget(item, row)

    def _add_empty_state(self, title: str, description: str):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 180))
        self.list_widget.addItem(item)
        card = QFrame()
        card.setStyleSheet("QFrame { background:#ffffff; border:1px solid #dfe8e1; border-radius:14px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title)
        title_label.setStyleSheet("color:#17211c; font-size:16px; font-weight:700; border:0;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        self.list_widget.setItemWidget(item, card)

    def _add_connection_item(self, event: dict):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 76))
        self.list_widget.addItem(item)
        row = QFrame()
        row.setStyleSheet("QFrame { background:#ffffff; border:1px solid #dfe8e1; border-radius:12px; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        started = event.get("event") == "started"
        badge = QLabel("DIMULAI" if started else "DIHENTIKAN")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = "#176b49" if started else "#68756e"
        background = "#e7f4ec" if started else "#edf3ef"
        badge.setStyleSheet(f"color:{color}; background:{background}; border:0; border-radius:9px; padding:6px 9px; font-size:9px; font-weight:700;")
        layout.addWidget(badge)

        details = QVBoxLayout()
        details.setSpacing(3)
        folder_path = str(event.get("folder_path") or "")
        folder_name = str(event.get("folder_name") or PureWindowsPath(folder_path.replace("/", "\\")).name or "Folder bersama")
        title = QLabel(f"Sesi {('dimulai' if started else 'dihentikan')} · {folder_name}")
        title.setStyleSheet("color:#17211c; font-size:13px; font-weight:600; border:0;")
        host = event.get("host") or "Alamat belum diketahui"
        port = event.get("port")
        mode = "Hanya baca" if event.get("read_only") else "Baca-tulis"
        details_text = f"{host}:{port} · {mode}" if port else f"{host} · {mode}"
        subtitle = QLabel(details_text)
        subtitle.setStyleSheet("color:#68756e; font-size:11px; border:0;")
        details.addWidget(title)
        details.addWidget(subtitle)
        layout.addLayout(details, 1)

        timestamp = event.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp).astimezone().strftime("%d %b %Y, %H:%M")
        except (TypeError, ValueError):
            pass
        date_label = QLabel(timestamp)
        date_label.setStyleSheet("color:#68756e; font-size:10px; border:0;")
        layout.addWidget(date_label)
        self.list_widget.setItemWidget(item, row)

    def _add_transfer_item(self, event: dict):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 76))
        self.list_widget.addItem(item)
        row = QFrame()
        row.setStyleSheet("QFrame { background:#ffffff; border:1px solid #dfe8e1; border-radius:12px; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        direction = str(event.get("direction", "download"))
        uploaded = direction == "upload"
        badge = QLabel("DIUNGGAH" if uploaded else "DIUNDUH")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = "#176b49" if uploaded else "#3065a5"
        background = "#e7f4ec" if uploaded else "#eaf1fb"
        badge.setStyleSheet(f"color:{color}; background:{background}; border:0; border-radius:9px; padding:6px 9px; font-size:9px; font-weight:700;")
        layout.addWidget(badge)

        details = QVBoxLayout()
        details.setSpacing(3)
        name = QLabel(str(event.get("file_name") or "Berkas"))
        name.setStyleSheet("color:#17211c; font-size:13px; font-weight:600; border:0;")
        client = str(event.get("client") or "Klien tidak diketahui")
        share = str(event.get("share") or "")
        subtitle = QLabel(f"HP · {client}" + (f" · {share}" if share else ""))
        subtitle.setStyleSheet("color:#68756e; font-size:11px; border:0;")
        details.addWidget(name)
        details.addWidget(subtitle)
        layout.addLayout(details, 1)

        try:
            timestamp = datetime.fromisoformat(str(event.get("timestamp", ""))).astimezone().strftime("%d %b %Y, %H:%M")
        except (TypeError, ValueError):
            timestamp = ""
        size = int(event.get("size_bytes", 0) or 0)
        date_label = QLabel(f"{self._format_size(size)}\n{timestamp}")
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        date_label.setStyleSheet("color:#68756e; font-size:10px; border:0;")
        layout.addWidget(date_label)
        self.list_widget.setItemWidget(item, row)

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(max(0, size))
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024

    def _clear_connections(self):
        if not self.history_manager.get_connection_history():
            return
        reply = QMessageBox.question(
            self,
            "Hapus riwayat koneksi?",
            "Hapus catatan sesi koneksi dari PC? Daftar folder tersimpan tidak akan dihapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_connection_history()
            self._current_page = 0
            self._refresh()

    def _clear_current_history(self):
        if self._view == "transfers":
            if not self.history_manager.get_transfer_history():
                return
            reply = QMessageBox.question(
                self,
                "Hapus riwayat transfer?",
                "Hapus catatan transfer yang diterima PC?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.history_manager.clear_transfer_history()
                self._current_page = 0
                self._refresh()
            return
        if self._view == "connections":
            self._clear_connections()
