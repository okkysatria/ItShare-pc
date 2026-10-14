"""
ui/page_folders.py - Folder management page.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame, QSizePolicy, QFileDialog, QMessageBox,
    QStyledItemDelegate, QStyleOptionViewItem, QApplication, QBoxLayout, QScrollArea,
    QToolButton, QGridLayout, QGraphicsBlurEffect
)
from PySide6.QtGui import QFont, QColor, QPainter, QFontMetrics, QPixmap, QIcon, QPen
from PySide6.QtCore import QRect

from core.smb_server import SMBServerManager
from core.history import HistoryManager
from core.session import ShareSession
from ui.styles import BTN_PRIMARY, BTN_DANGER, BTN_NORMAL, MAIN_STYLE, theme_stylesheet

logger = logging.getLogger(__name__)

COL_NAME   = 0
COL_STATUS = 1
COL_MODE   = 2
COL_PORT   = 3
COL_ACTION = 4

class TwoLineDelegate(QStyledItemDelegate):
    """Custom delegate to paint folder name (bold) + full path (small grey) with elide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = False

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        self.initStyleOption(option, index)
        rect: QRect = option.rect
        is_selected = bool(option.state & option.state.State_Selected)
        if self.dark_mode:
            painter.fillRect(rect, QColor("#303030" if is_selected else "#1e1e1e"))
        else:
            painter.fillRect(rect, QColor("#dff3e8" if is_selected else "#ffffff"))
        left = rect.left() + 16
        width = rect.width() - 20

        folder_name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        folder_path = index.data(Qt.ItemDataRole.UserRole + 1) or ""

        text_color = QColor("#e4e4e4" if self.dark_mode else "#1e293b")
        path_color = QColor("#a0a0a0" if self.dark_mode else "#86948b")

        name_font = QFont(option.font)
        name_font.setBold(True)
        name_font.setPointSize(option.font.pointSize())
        painter.setFont(name_font)
        painter.setPen(text_color)
        name_fm = QFontMetrics(name_font)
        name_elided = name_fm.elidedText(folder_name, Qt.TextElideMode.ElideRight, width)
        painter.drawText(left, rect.top() + 14, name_elided)

        path_font = QFont(option.font)
        path_font.setPointSizeF(option.font.pointSizeF() * 0.85)
        painter.setFont(path_font)
        painter.setPen(path_color)
        path_fm = QFontMetrics(path_font)
        path_elided = path_fm.elidedText(folder_path, Qt.TextElideMode.ElideMiddle, width)
        painter.drawText(left, rect.top() + 34, path_elided)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 52)

class PageFolders(QWidget):
    session_started = Signal(ShareSession)
    session_stopped = Signal()

    def __init__(self, smb_manager: SMBServerManager, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.smb_manager = smb_manager
        self.history_manager = history_manager
        self._current_session: Optional[ShareSession] = None
        self._sessions_by_path = {}
        self._refreshing_table = False
        self._current_page = 0
        self._dark_mode = False
        self._page_size = 8
        self._show_folder_paths = True
        self._qr_hidden = False
        self._qr_hide_by_default = False
        self._qr_default_initialized = False
        self._connection_was_active = False
        self._filtered_folders = []
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.dashboard_scroll = QScrollArea(self)
        self.dashboard_scroll.setWidgetResizable(True)
        self.dashboard_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.dashboard_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        dashboard_body = QWidget()
        dashboard_body.setObjectName("DashboardBody")
        dashboard_body.setStyleSheet("background:#f5f7f3;")
        root = QVBoxLayout(dashboard_body)
        self.dashboard_layout = root
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(16)

        hero = QFrame()
        hero.setStyleSheet("QFrame { background: transparent; }")
        hero_layout = QHBoxLayout(hero)
        self.hero_layout = hero_layout
        hero_layout.setContentsMargins(0, 0, 0, 0)
        intro = QVBoxLayout()
        intro.setSpacing(4)
        eyebrow = QLabel("BERBAGI DI JARINGAN LOKAL")
        eyebrow.setStyleSheet("color:#176b49; font-size:10px; font-weight:700; letter-spacing:1px;")
        title = QLabel("Bagikan folder ke Android")
        title.setStyleSheet("color:#17211c; font-size:25px; font-weight:700;")
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        hero_layout.addLayout(intro, 1)
        self.hero_action = QPushButton("Tambah Folder Baru")
        self.hero_action.setStyleSheet(BTN_PRIMARY)
        self.hero_action.setMinimumHeight(42)
        self.hero_action.clicked.connect(self._on_hero_action)
        hero_layout.addWidget(self.hero_action, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(hero)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        self.content_layout = content_layout
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        folder_panel = QFrame()
        folder_panel.setStyleSheet("QFrame { background:#ffffff; border:1px solid #dfe8e1; border-radius:16px; }")
        folder_layout = QVBoxLayout(folder_panel)
        self.folder_layout = folder_layout
        folder_layout.setContentsMargins(16, 14, 16, 14)
        folder_layout.setSpacing(10)
        folder_heading = QHBoxLayout()
        folder_title = QLabel("FOLDER DIBAGIKAN")
        folder_title.setStyleSheet("color:#176b49; font-size:10px; font-weight:700; letter-spacing:1px; border:0;")
        folder_heading.addWidget(folder_title)
        folder_heading.addStretch()
        folder_layout.addLayout(folder_heading)
        content_layout.addWidget(folder_panel, 1)

        self.connection_panel = QFrame()
        self.connection_panel.setMinimumWidth(250)
        self.connection_panel.setMaximumWidth(330)
        self.connection_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.connection_panel.setStyleSheet("QFrame#ConnectionPanel { background:#ffffff; border:1px solid #dfe8e1; border-radius:16px; }")
        self.connection_panel.setObjectName("ConnectionPanel")
        connection_layout = QVBoxLayout(self.connection_panel)
        connection_layout.setContentsMargins(18, 18, 18, 18)
        connection_layout.setSpacing(12)
        connection_title = QLabel("KONEKSI ANDROID")
        connection_title.setStyleSheet("color:#176b49; background:transparent; font-size:10px; font-weight:700; letter-spacing:1px; border:0;")
        self.connection_state = QLabel("Kode QR belum tersedia")
        self.connection_state.setWordWrap(True)
        self.connection_state.setFixedHeight(42)
        self.connection_state.setStyleSheet("color:#17211c; background:transparent; font-size:17px; font-weight:700; border:0;")
        self.qr_preview = QLabel("QR belum aktif")
        self.qr_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_preview.setFixedSize(180, 180)
        self.qr_preview.setWordWrap(True)
        self.qr_preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.qr_preview.setStyleSheet("color:#87948c; background:#f6f9f7; border:1px dashed #cbd8cf; border-radius:12px; font-size:11px;")
        self._qr_blur_effect = QGraphicsBlurEffect(self.qr_preview)
        self._qr_blur_effect.setBlurRadius(18)
        self._qr_blur_effect.setEnabled(False)
        self.qr_preview.setGraphicsEffect(self._qr_blur_effect)
        self.qr_holder = QWidget()
        self.qr_holder.setFixedHeight(200)
        qr_holder_layout = QGridLayout(self.qr_holder)
        qr_holder_layout.setContentsMargins(0, 0, 0, 0)
        qr_holder_layout.addWidget(self.qr_preview, 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.btn_qr_visibility = QToolButton(self.qr_holder)
        self.btn_qr_visibility.setFixedSize(30, 30)
        self.btn_qr_visibility.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_qr_visibility.setStyleSheet("QToolButton { background:#ffffff; border:1px solid #dfe8e1; border-radius:15px; padding:4px; } QToolButton:hover { background:#eaf4ef; }")
        self.btn_qr_visibility.clicked.connect(self._toggle_qr_visibility)
        qr_holder_layout.addWidget(self.btn_qr_visibility, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self._set_qr_visibility_icon()
        self.connection_details = QLabel("")
        self.connection_details.setWordWrap(True)
        self.connection_details.setFixedHeight(60)
        self.connection_details.setStyleSheet("color:#68756e; background:transparent; font-size:12px; border:0;")
        self.btn_connection_qr = QPushButton("Perbesar QR SMB")
        self.btn_connection_qr.setStyleSheet(BTN_PRIMARY)
        self.btn_connection_qr.clicked.connect(self.show_qr_dialog)
        self.btn_connection_qr.setEnabled(False)
        self.btn_copy_address = QPushButton("Salin Alamat")
        self.btn_copy_address.setStyleSheet(BTN_NORMAL)
        self.btn_copy_address.clicked.connect(self._copy_connection_address)
        self.btn_copy_address.setEnabled(False)
        for widget in (connection_title, self.connection_state, self.qr_holder, self.connection_details, self.btn_connection_qr, self.btn_copy_address):
            connection_layout.addWidget(widget)
        self.connection_details.hide()
        connection_layout.addStretch()
        content_layout.addWidget(self.connection_panel, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(content, 1)
        self.dashboard_scroll.setWidget(dashboard_body)
        outer.addWidget(self.dashboard_scroll)

        toolbar = QFrame()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet("QFrame { background:transparent; border:0; }")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(10)

        lbl_title = QLabel("Folder Saya")
        lbl_title.hide()
        tb_layout.addWidget(lbl_title)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cari folder...")
        self.search_bar.setMinimumWidth(120)
        self.search_bar.setMaximumWidth(260)
        self.search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_bar.textChanged.connect(self._filter_table)
        tb_layout.addWidget(self.search_bar, 1)
        self.btn_open_folder = QPushButton("Buka di File Manager")
        self.btn_open_folder.setStyleSheet(BTN_NORMAL)
        self.btn_open_folder.setToolTip("Buka folder yang dipilih di Windows File Manager")
        self.btn_open_folder.clicked.connect(self._open_folder_in_file_manager)
        self.btn_open_folder.setEnabled(False)
        tb_layout.addWidget(self.btn_open_folder)

        folder_layout.addWidget(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Folder", "Status", "Mode", "Port", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(COL_MODE, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(COL_PORT, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(COL_STATUS, 120)
        self.table.setColumnWidth(COL_MODE, 78)
        self.table.setColumnWidth(COL_PORT, 60)
        self.table.setColumnWidth(COL_ACTION, 244)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._apply_table_theme()
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.itemSelectionChanged.connect(self._on_folder_selection_changed)
        self._name_delegate = TwoLineDelegate(self.table)
        self.table.setItemDelegateForColumn(COL_NAME, self._name_delegate)
        folder_layout.addWidget(self.table, stretch=1)

        self.empty_frame = QFrame()
        empty_layout = QVBoxLayout(self.empty_frame)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_icon = QLabel()
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon_folder.svg"
        if icon_path.is_file():
            self.lbl_empty_icon.setPixmap(QIcon(str(icon_path)).pixmap(48, 48))
        self.lbl_empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty_txt = QLabel("Belum ada folder dibagikan")
        lbl_empty_txt.setObjectName("emptyFolderTitle")
        lbl_empty_txt.setStyleSheet("font-size: 15px; color: #86948b; font-weight: 600;")
        lbl_empty_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty_sub = QLabel("Tambah folder untuk mulai")
        lbl_empty_sub.setObjectName("emptyFolderHint")
        lbl_empty_sub.setStyleSheet("font-size: 12px; color: #cad5cd;")
        lbl_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        empty_layout.addWidget(self.lbl_empty_icon)
        empty_layout.addSpacing(8)
        empty_layout.addWidget(lbl_empty_txt)
        empty_layout.addWidget(lbl_empty_sub)
        empty_layout.addStretch()
        folder_layout.addWidget(self.empty_frame, stretch=1)

        self.pagination = QWidget()
        pagination_layout = QHBoxLayout(self.pagination)
        pagination_layout.setContentsMargins(0, 2, 0, 0)
        self.btn_prev_page = QPushButton("‹ Sebelumnya")
        self.btn_prev_page.setStyleSheet(BTN_NORMAL)
        self.btn_prev_page.clicked.connect(lambda: self._change_page(-1))
        self.lbl_page = QLabel("")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setStyleSheet("color:#68756e; font-size:11px;")
        self.btn_next_page = QPushButton("Berikutnya ›")
        self.btn_next_page.setStyleSheet(BTN_NORMAL)
        self.btn_next_page.clicked.connect(lambda: self._change_page(1))
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next_page)
        folder_layout.addWidget(self.pagination)
        self._update_connection_panel()
        self._apply_responsive_layout()

    def _on_hero_action(self):
        self.focus_add_folder()

    def _copy_connection_address(self):
        if not self._current_session:
            return
        from PySide6.QtWidgets import QApplication
        session = self._current_session
        QApplication.clipboard().setText(f"smb://{session.host_ip}:{session.port}/{session.share_name}")
        self.btn_copy_address.setText("Alamat Disalin")
        QTimer.singleShot(1600, lambda: self.btn_copy_address.setText("Salin Alamat"))

    def _update_connection_panel(self):
        active = bool(self._current_session and self.smb_manager.is_running())
        if active and not self._connection_was_active:
            self._qr_hidden = self._qr_hide_by_default
        self._connection_was_active = active
        self.hero_action.setText("Tambah Folder Baru")
        self.hero_action.setStyleSheet(BTN_PRIMARY)
        self.btn_connection_qr.setEnabled(active)
        self.btn_copy_address.setEnabled(active)
        self.btn_qr_visibility.setEnabled(active)
        self.connection_details.setVisible(active)
        if active:
            session = self._current_session
            self.connection_state.setText("Pindai untuk terhubung")
            try:
                import json
                from core.qr_generator import build_smb_payload, render_to_pixmap
                pixmap = render_to_pixmap(json.dumps(build_smb_payload(session)))
                self.qr_preview.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.qr_preview.setText("")
                self._qr_blur_effect.setEnabled(self._qr_hidden)
            except Exception as error:
                self.qr_preview.setPixmap(QPixmap())
                self.qr_preview.setText(f"QR gagal dibuat: {error}")
                self._qr_blur_effect.setEnabled(False)
            self.connection_details.setText(
                f"smb://{session.host_ip}:{session.port}/{session.share_name}\n"
                f"Pengguna: {session.username}"
            )
        else:
            self.connection_state.setText("Kode QR belum tersedia")
            self.qr_preview.setPixmap(QPixmap())
            self.qr_preview.setText("QR belum aktif")
            self._qr_blur_effect.setEnabled(False)
            self.connection_details.setText("")
        self._set_qr_visibility_icon()
        self._apply_page_language()

    def _set_qr_visibility_icon(self):
        icon_pixmap = QPixmap(20, 20)
        icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon_pixmap)
        color = QColor("#e4ede7" if self._dark_mode else "#176b59")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 5, 16, 10)
        painter.setBrush(color)
        painter.drawEllipse(8, 8, 4, 4)
        if self._qr_hidden:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(3, 17, 17, 3)
        painter.end()
        self.btn_qr_visibility.setIcon(QIcon(icon_pixmap))
        self.btn_qr_visibility.setIconSize(QSize(20, 20))
        if self._dark_mode:
            self.btn_qr_visibility.setStyleSheet("QToolButton { background:#292929; border:1px solid #454545; border-radius:15px; padding:4px; } QToolButton:hover { background:#353535; }")
        else:
            self.btn_qr_visibility.setStyleSheet("QToolButton { background:#ffffff; border:1px solid #dfe8e1; border-radius:15px; padding:4px; } QToolButton:hover { background:#eaf4ef; }")
        language = self.window().property("_itshare_language") or "en"
        self.btn_qr_visibility.setToolTip(
            ("Tampilkan QR" if self._qr_hidden else "Sembunyikan QR") if language == "id"
            else ("Show QR code" if self._qr_hidden else "Hide QR code")
        )

    def _toggle_qr_visibility(self):
        self._qr_hidden = not self._qr_hidden
        self._qr_blur_effect.setEnabled(self._qr_hidden and bool(self.qr_preview.pixmap()))
        self._set_qr_visibility_icon()

    def _apply_page_language(self):
        from ui.i18n import apply_language
        from ui.styles import apply_theme
        top_level = self.window()
        language = top_level.property("_itshare_language") or "en"
        theme = top_level.property("_itshare_theme") or "system"
        apply_theme(self, theme)
        apply_language(self, language)
        self._dark_mode = theme_stylesheet(theme) != MAIN_STYLE
        self._name_delegate.set_dark_mode(self._dark_mode)
        self._set_qr_visibility_icon()

    def set_dark_mode(self, dark: bool):
        changed = self._dark_mode != bool(dark)
        self._dark_mode = bool(dark)
        self._name_delegate.set_dark_mode(self._dark_mode)
        self._apply_table_theme()
        self._set_qr_visibility_icon()
        self.table.viewport().update()
        if changed:
            self._refresh_table()

    def _apply_table_theme(self):
        """Keep the dashboard table header, cells and selection on one palette."""
        if self._dark_mode:
            background, foreground = "#1e1e1e", "#e4ede7"
            header_bg, header_fg = "#292929", "#d4dfd7"
            border, hover, selected = "#303030", "#292929", "#353535"
        else:
            background, foreground = "#ffffff", "#1e293b"
            header_bg, header_fg = "#edf8f1", "#52635a"
            border, hover, selected = "#edf3ef", "#edf8f1", "#dff3e8"
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {background};
                color: {foreground};
                border: none;
                outline: none;
                selection-background-color: {selected};
                selection-color: {foreground};
            }}
            QTableWidget::item {{ padding: 0px; border-bottom: 1px solid {border}; }}
            QTableWidget::item:hover {{ background-color: {hover}; }}
            QTableWidget::item:selected {{ background-color: {selected}; color: {foreground}; }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_fg};
                padding: 8px;
                font-weight: 600;
                font-size: 12px;
                border: none;
                border-bottom: 1px solid {border};
                border-right: 1px solid {border};
            }}
            QTableCornerButton::section {{ background-color: {header_bg}; border: none; }}
        """)

    def _refresh_table(self):
        folders = self.history_manager.get_recent_folders()
        query = self.search_bar.text().strip().casefold()
        selected_path = self._selected_folder_path()
        self._filtered_folders = [
            path for path in folders
            if not query or query in path.casefold() or query in Path(path).name.casefold()
            or query in self.history_manager.get_folder_alias(path).casefold()
        ]
        self._refreshing_table = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        if not self._filtered_folders:
            self.table.setVisible(False)
            self.empty_frame.setVisible(True)
            self.pagination.setVisible(False)
            for label in self.empty_frame.findChildren(QLabel):
                if label.objectName() == "emptyFolderTitle":
                    label.setText("Folder tidak ditemukan" if query else "Belum ada folder dibagikan")
                elif label.objectName() == "emptyFolderHint":
                    label.setText("Coba kata kunci lain." if query else "Tambah folder untuk mulai")
            self.table.blockSignals(False)
            self._refreshing_table = False
            self._current_session = None
            self._update_connection_panel()
            self._update_open_folder_action()
            self._apply_page_language()
            return

        self.table.setVisible(True)
        self.empty_frame.setVisible(False)
        page_count = max(1, (len(self._filtered_folders) + self._page_size - 1) // self._page_size)
        self._current_page = max(0, min(self._current_page, page_count - 1))
        start = self._current_page * self._page_size
        visible_folders = self._filtered_folders[start:start + self._page_size]

        for folder_path in visible_folders:
            self._add_table_row(folder_path)
        selected_key = self._path_key(selected_path) if selected_path else None
        active_key = next((key for key in self._sessions_by_path if key in {
            self._path_key(path) for path in visible_folders
        }), None)
        preferred_key = selected_key if selected_key in {self._path_key(path) for path in visible_folders} else active_key
        if preferred_key is None and visible_folders:
            preferred_key = self._path_key(visible_folders[0])
        for row, path in enumerate(visible_folders):
            if self._path_key(path) == preferred_key:
                self.table.selectRow(row)
                break
        self.table.blockSignals(False)
        self._refreshing_table = False
        self._on_folder_selection_changed()
        self.pagination.setVisible(page_count > 1)
        self.lbl_page.setText(f"Halaman {self._current_page + 1} dari {page_count} · {len(self._filtered_folders)} folder")
        self.btn_prev_page.setEnabled(self._current_page > 0)
        self.btn_next_page.setEnabled(self._current_page < page_count - 1)
        self._update_open_folder_action()
        self._apply_page_language()

    def _change_page(self, delta: int):
        self._current_page += delta
        self._refresh_table()

    def _add_table_row(self, folder_path: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 52)

        display_name = self.history_manager.get_folder_alias(folder_path) or Path(folder_path).name
        name_item = QTableWidgetItem(display_name)
        name_item.setData(Qt.ItemDataRole.UserRole, folder_path)
        name_item.setData(
            Qt.ItemDataRole.UserRole + 1,
            folder_path if self._show_folder_paths else "",
        )
        name_item.setToolTip(folder_path)
        self.table.setItem(row, COL_NAME, name_item)

        row_session = self._sessions_by_path.get(self._path_key(folder_path))
        is_active = bool(row_session and self.smb_manager.is_running())
        status_widget = QWidget()
        status_widget.setStyleSheet("background: transparent;")
        sl = QHBoxLayout(status_widget)
        sl.setContentsMargins(8, 0, 8, 0)
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_st = QLabel("●  Aktif" if is_active else "○  Tidak aktif")
        if is_active:
            fg = "#86efac" if self._dark_mode else "#176b49"
        else:
            fg = "#c3c7c5" if self._dark_mode else "#68756e"
        lbl_st.setStyleSheet(
            f"color:{fg}; background:transparent; "
            "padding:4px 0; font-size:11px; font-weight:600;"
        )
        lbl_st.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(lbl_st)
        self.table.setCellWidget(row, COL_STATUS, status_widget)

        mode_item = QTableWidgetItem("Hanya Baca" if (is_active and row_session.read_only) else ("Baca & Tulis" if is_active else "—"))
        mode_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_item.setForeground(QColor("#68756e"))
        self.table.setItem(row, COL_MODE, mode_item)

        port_item = QTableWidgetItem(str(row_session.port) if is_active else "—")
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        port_item.setForeground(QColor("#68756e"))
        self.table.setItem(row, COL_PORT, port_item)

        action_widget = QWidget()
        action_widget.setStyleSheet("background: transparent;")
        al = QHBoxLayout(action_widget)
        al.setContentsMargins(6, 6, 6, 6)
        al.setSpacing(6)

        if is_active:
            btn_stop = QPushButton("■  Hentikan")
            btn_stop.setToolTip("Hentikan share folder ini")
            btn_stop.setStyleSheet(BTN_DANGER)
            btn_stop.setFixedHeight(32)
            btn_stop.clicked.connect(lambda checked=False, fp=folder_path: self._stop_folder_share(fp))
            al.addWidget(btn_stop)
        else:
            btn_start = QPushButton("▶  Mulai")
            btn_start.setToolTip("Mulai server SMB untuk folder ini")
            btn_start.setStyleSheet(BTN_NORMAL)
            btn_start.setFixedHeight(32)
            btn_start.clicked.connect(lambda checked=False, fp=folder_path: self._start_for_folder(fp))
            al.addWidget(btn_start)

        icon_name = "icon_settings_dark.svg" if self._dark_mode else "icon_settings.svg"
        icon_path = Path(__file__).resolve().parent.parent / "assets" / icon_name
        btn_configure = QPushButton()
        btn_configure.setIcon(QIcon(str(icon_path)))
        btn_configure.setIconSize(QSize(16, 16))
        btn_configure.setFixedSize(34, 32)
        btn_configure.setToolTip("Pengaturan folder")
        btn_configure.setAccessibleName("Pengaturan folder")
        btn_configure.setStyleSheet(BTN_NORMAL)
        btn_configure.clicked.connect(lambda checked=False, fp=folder_path: self._configure_folder(fp))
        btn_remove = QPushButton("Hapus")
        btn_remove.setToolTip("Hapus dari daftar cepat saja; folder dan isinya tetap ada di PC")
        btn_remove.setStyleSheet(BTN_NORMAL)
        btn_remove.setFixedHeight(32)
        btn_remove.clicked.connect(lambda checked, fp=folder_path: self._remove_folder_from_list(fp))
        al.addWidget(btn_remove)
        al.addWidget(btn_configure)

        self.table.setCellWidget(row, COL_ACTION, action_widget)

    def _filter_table(self, text: str):
        self._current_page = 0
        self._refresh_table()

    def _remove_folder_from_list(self, folder_path: str):
        if self._path_key(folder_path) in self._sessions_by_path and self.smb_manager.is_running():
            QMessageBox.information(self, "Share Sedang Aktif", "Hentikan share dari baris folder terlebih dahulu sebelum menghapusnya dari daftar cepat.")
            return
        answer = QMessageBox.question(
            self,
            "Hapus dari daftar folder?",
            f"{Path(folder_path).name} akan dihapus dari daftar cepat ItShare. Folder dan isinya di PC tidak dihapus. Jika sedang aktif, server tetap berjalan sampai dihentikan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.history_manager.remove_recent_folder(folder_path)
            self._refresh_table()

    def _apply_responsive_layout(self):
        aspect_ratio = self.width() / max(1, self.height())
        narrow = self.width() < 900 or aspect_ratio < 1.25
        self.content_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )
        if narrow:
            self.dashboard_layout.setContentsMargins(14, 14, 14, 14)
            self.hero_layout.setDirection(QBoxLayout.Direction.TopToBottom if self.width() < 700 or aspect_ratio < 0.9 else QBoxLayout.Direction.LeftToRight)
            self.connection_panel.setMinimumWidth(0)
            self.connection_panel.setMaximumWidth(16777215)
            self.table.setColumnHidden(COL_MODE, self.width() < 780)
            self.table.setColumnHidden(COL_PORT, self.width() < 780)
            self.table.setColumnHidden(COL_STATUS, self.width() < 620)
        else:
            self.dashboard_layout.setContentsMargins(24, 18, 24, 18)
            self.hero_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self.connection_panel.setMinimumWidth(250)
            self.connection_panel.setMaximumWidth(330)
            for column in (COL_STATUS, COL_MODE, COL_PORT):
                self.table.setColumnHidden(column, False)

    def apply_ui_preferences(self, settings: dict):
        requested_page_size = int(settings.get("folders_per_page", 8))
        self._page_size = requested_page_size if requested_page_size in {8, 12, 20} else 8
        self._show_folder_paths = bool(settings.get("show_folder_paths", True))
        hide_qr_by_default = bool(settings.get("hide_qr_by_default", False))
        if not self._qr_default_initialized:
            self._qr_hide_by_default = hide_qr_by_default
            self._qr_default_initialized = True
        elif hide_qr_by_default != self._qr_hide_by_default:
            self._qr_hide_by_default = hide_qr_by_default
            if self._connection_was_active:
                self._qr_hidden = hide_qr_by_default
                self._qr_blur_effect.setEnabled(self._qr_hidden and bool(self.qr_preview.pixmap()))
                self._set_qr_visibility_icon()
        self.folder_layout.setSpacing(10)
        self.dashboard_layout.setSpacing(16)
        self._refresh_table()

    def set_icon_theme(self, dark: bool):
        icon_name = "icon_folder_dark.svg" if dark else "icon_folder.svg"
        icon_path = Path(__file__).resolve().parent.parent / "assets" / icon_name
        if icon_path.is_file():
            self.lbl_empty_icon.setPixmap(QIcon(str(icon_path)).pixmap(48, 48))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _on_row_double_click(self, index):
        item = self.table.item(index.row(), COL_NAME)
        if item:
            folder_path = item.data(Qt.ItemDataRole.UserRole) or item.text()
            self._start_for_folder(folder_path)

    def _selected_folder_path(self):
        row = self.table.currentRow()
        item = self.table.item(row, COL_NAME) if row >= 0 else None
        return (item.data(Qt.ItemDataRole.UserRole) or item.text()) if item else None

    def _select_folder_in_table(self, folder_path: str):
        wanted = self._path_key(folder_path)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            if item and self._path_key(item.data(Qt.ItemDataRole.UserRole) or item.text()) == wanted:
                self.table.setCurrentCell(row, COL_NAME)
                self.table.selectRow(row)
                return True
        return False

    @staticmethod
    def _path_key(folder_path):
        return os.path.normcase(os.path.normpath(str(folder_path))) if folder_path else ""

    def _on_folder_selection_changed(self):
        if self._refreshing_table:
            return
        folder_path = self._selected_folder_path()
        self._current_session = self._sessions_by_path.get(self._path_key(folder_path)) if folder_path else None
        self._update_open_folder_action()
        self._update_connection_panel()

    def _update_open_folder_action(self):
        path = self._selected_folder_path() or (self._current_session.folder_path if self._current_session else None)
        self.btn_open_folder.setEnabled(bool(path and os.path.isdir(path)))

    def _open_folder_in_file_manager(self):
        path = self._selected_folder_path() or (self._current_session.folder_path if self._current_session else None)
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "Folder Tidak Tersedia", "Pilih folder yang masih tersedia di PC.")
            self._update_open_folder_action()
            return
        try:
            os.startfile(path)
        except OSError as error:
            QMessageBox.critical(self, "Tidak Dapat Membuka File Manager", str(error))

    def _start_for_folder(self, folder_path: str):
        """Start sharing with saved defaults, without opening a setup dialog."""
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Folder Tidak Tersedia", "Pilih folder yang masih tersedia di PC.")
            self._refresh_table()
            return
        settings = self.history_manager.get_settings()
        from core.credentials import generate_username, generate_password
        from core.network import get_local_ips
        ips = get_local_ips()
        existing = self.smb_manager.active_sessions if self.smb_manager.is_running() else []
        import re
        display_name = self.history_manager.get_folder_alias(folder_path) or Path(folder_path).name
        share_name = re.sub(r"[^A-Za-z0-9_$-]+", "_", display_name).strip("_-")[:80] or "ItShare"
        if existing and any(item.share_name.casefold() == share_name.casefold() for item in existing):
            candidate = share_name
            share_name = candidate[:80]
            used_names = {item.share_name.casefold() for item in existing}
            suffix = 2
            while share_name.casefold() in used_names:
                share_name = f"{candidate[:70]}_{suffix}"
                suffix += 1
        session = ShareSession(
            folder_path=folder_path,
            username=generate_username(),
            password=generate_password(),
            port=int(settings.get("default_port", 4455)),
            read_only=bool(settings.get("default_read_only", True)),
            timeout_minutes=max(0, int(settings.get("default_timeout_minutes", 0))),
            share_name=share_name,
            host_ip=ips[0][1] if ips else "127.0.0.1",
        )
        self._launch_server(session)

    def _configure_folder(self, folder_path: str):
        """Open optional share settings for this folder."""
        from ui.dialogs import AddShareDialog
        dlg = AddShareDialog(
            folder_path=folder_path,
            settings=self.history_manager.get_settings(),
            parent=self,
            display_name=self.history_manager.get_folder_alias(folder_path),
        )
        self._translate_dialog(dlg)
        if dlg.exec():
            session = dlg.get_session()
            session.replaces_folder_path = folder_path
            self.history_manager.set_folder_alias(session.folder_path, dlg.get_display_name())
            self._refresh_table()
            self._launch_server(session)

    def focus_add_folder(self):
        from ui.dialogs import AddShareDialog
        dlg = AddShareDialog(settings=self.history_manager.get_settings(), parent=self)
        self._translate_dialog(dlg)
        if dlg.exec():
            session = dlg.get_session()
            self.history_manager.set_folder_alias(session.folder_path, dlg.get_display_name())
            self._launch_server(session)

    def _translate_dialog(self, dialog):
        from ui.i18n import apply_language
        from ui.styles import apply_theme
        top_level = self.window()
        language = top_level.property("_itshare_language") or "en"
        theme = top_level.property("_itshare_theme") or "system"
        apply_theme(dialog, theme)
        apply_language(dialog, language)

    def restore_active_session(self, session: ShareSession):
        self.restore_active_sessions([session])

    def restore_active_sessions(self, sessions):
        """Restore every share from the detached SMB service after UI restart."""
        self._sessions_by_path = {self._path_key(session.folder_path): session for session in sessions}
        self._current_session = sessions[0] if sessions else None
        recent_paths = {
            self._path_key(path)
            for path in self.history_manager.get_recent_folders()
        }
        for session in sessions:
            if self._path_key(session.folder_path) not in recent_paths:
                self.history_manager.add_recent_folder(session.folder_path)
        self._refresh_table()
        self._update_connection_panel()
        if any(session.timeout_minutes > 0 for session in sessions):
            self._countdown_timer.start(1000)

    def _launch_server(self, session: ShareSession):
        old_sessions = self.smb_manager.active_sessions if self.smb_manager.is_running() else []
        session_key = self._path_key(session.folder_path)
        previous = next((
            item for item in old_sessions
            if self._path_key(item.folder_path) == session_key
            or self._path_key(item.folder_path) == self._path_key(getattr(session, "replaces_folder_path", ""))
        ), None)
        sessions = [item for item in old_sessions if item is not previous]
        sessions.append(session)
        if old_sessions:
            primary = old_sessions[0]
            session.port = primary.port
            session.host_ip = primary.host_ip
            session.username = primary.username
            session.password = primary.password
            names = [item.share_name.casefold() for item in sessions]
            base_name = session.share_name
            suffix = 2
            while names.count(session.share_name.casefold()) > 1:
                session.share_name = f"{base_name[:75]}_{suffix}"
                names[-1] = session.share_name.casefold()
                suffix += 1
            if session.share_name != base_name:
                self.history_manager.set_folder_alias(session.folder_path, session.share_name)
            for item in sessions[:-1]:
                item.port = primary.port
                item.host_ip = primary.host_ip
        ok, msg = self.smb_manager.start(session, sessions=sessions)
        if not ok:
            if old_sessions:
                restored, restore_message = self.smb_manager.start(old_sessions[0], sessions=old_sessions)
                if restored:
                    self._sessions_by_path = {self._path_key(item.folder_path): item for item in old_sessions}
                else:
                    self._sessions_by_path = {}
                    msg += f"\nShare sebelumnya juga gagal dipulihkan: {restore_message}"
                    self.session_stopped.emit()
            else:
                self._sessions_by_path = {}
            self._refresh_table()
            QMessageBox.critical(self, "Gagal Memulai Server", msg)
            return

        from core.network import get_local_ips
        ips = get_local_ips()
        if ips:
            session.host_ip = ips[0][1]

        if previous:
            self.history_manager.record_connection(previous, "stopped")
        replaced_path = getattr(session, "replaces_folder_path", "")
        if replaced_path and self._path_key(replaced_path) != self._path_key(session.folder_path):
            self.history_manager.remove_recent_folder(replaced_path)
        self.history_manager.add_recent_folder(session.folder_path)
        self.history_manager.record_connection(session, "started")
        self._sessions_by_path = {self._path_key(item.folder_path): item for item in sessions}
        self._current_session = session
        self._current_page = 0 if not previous else self._current_page
        self._refresh_table()
        self._select_folder_in_table(session.folder_path)

        self._update_connection_panel()

        if any(item.timeout_minutes > 0 for item in sessions):
            self._countdown_timer.start(1000)

        self.session_started.emit(session)

    def on_stop_share(self, confirm: bool = True):
        if self._current_session and confirm and self.history_manager.get_settings().get("confirm_before_stop", True):
            reply = QMessageBox.question(
                self,
                "Hentikan berbagi?",
                "Perangkat Android yang terhubung akan kehilangan akses ke folder ini.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if self._current_session:
            self._stop_folder_share(self._current_session.folder_path, confirm=False)

    def _stop_folder_share(self, folder_path: str, confirm: bool = True):
        key = self._path_key(folder_path)
        target = self._sessions_by_path.get(key)
        if not target:
            return
        if confirm and self.history_manager.get_settings().get("confirm_before_stop", True):
            reply = QMessageBox.question(
                self, "Hentikan berbagi?",
                f"Hentikan share folder '{Path(folder_path).name}'? Share folder lain tetap berjalan.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        old_sessions = list(self._sessions_by_path.values())
        remaining = [item for item in old_sessions if self._path_key(item.folder_path) != key]
        if remaining:
            ok, message = self.smb_manager.start(remaining[0], sessions=remaining)
            if not ok:
                restored, restore_message = self.smb_manager.start(old_sessions[0], sessions=old_sessions)
                if not restored:
                    self._sessions_by_path = {}
                    message += f"\nShare sebelumnya juga gagal dipulihkan: {restore_message}"
                    self._countdown_timer.stop()
                    self.session_stopped.emit()
                QMessageBox.critical(self, "Gagal Memperbarui Share", message)
                self._refresh_table()
                return
            self._sessions_by_path = {self._path_key(item.folder_path): item for item in remaining}
        else:
            self.smb_manager.stop()
            self._sessions_by_path = {}
            self._countdown_timer.stop()
        self.history_manager.record_connection(target, "stopped")
        self._refresh_table()
        if remaining:
            self._select_folder_in_table(remaining[0].folder_path)
            self.session_started.emit(remaining[0])
        else:
            self.session_stopped.emit()

    def on_regenerate(self):
        """Regenerate credentials (called from main window disconnect action)."""
        if not self._current_session:
            return
        from core.credentials import generate_username, generate_password
        self._current_session.username = generate_username()
        self._current_session.password = generate_password()
        sessions = list(self._sessions_by_path.values())
        ok, msg = self.smb_manager.start(self._current_session, sessions=sessions)
        if ok:
            self._refresh_table()
            self._update_connection_panel()
        else:
            QMessageBox.critical(self, "Gagal Memperbarui QR", msg)

    def _tick_countdown(self):
        sessions = list(self._sessions_by_path.values())
        if not sessions:
            self._countdown_timer.stop()
            return
        expired = [session for session in sessions if session.is_expired]
        if expired:
            self._countdown_timer.stop()
            remaining = [session for session in sessions if not session.is_expired]
            for session in expired:
                self.history_manager.record_connection(session, "stopped")
            if remaining:
                ok, message = self.smb_manager.start(remaining[0], sessions=remaining)
                if ok:
                    self._sessions_by_path = {self._path_key(item.folder_path): item for item in remaining}
                    self._refresh_table()
                    self._select_folder_in_table(remaining[0].folder_path)
                    self.session_started.emit(remaining[0])
                else:
                    QMessageBox.critical(self, "Gagal Memperbarui Share", message)
                    self._sessions_by_path = {}
                    self.smb_manager.stop()
                    self._refresh_table()
                    self.session_stopped.emit()
            else:
                self.smb_manager.stop()
                self._sessions_by_path = {}
                self._refresh_table()
                self.session_stopped.emit()
            QMessageBox.information(
                self, "Sesi Berakhir",
                f"{len(expired)} share yang melewati batas waktu dihentikan."
                if remaining else "Semua sesi share telah melewati batas waktu dan server dihentikan.",
            )
            if any(item.timeout_minutes > 0 for item in remaining):
                self._countdown_timer.start(1000)

    def show_qr_dialog(self):
        if not self._current_session:
            QMessageBox.information(self, "Tidak ada sesi", "Mulai server terlebih dahulu.")
            return
        from ui.dialogs import itshareDialog
        dlg = itshareDialog(self._current_session, parent=self)
        self._translate_dialog(dlg)
        dlg.exec()

    def show_wifi_dialog(self):
        from ui.dialogs import WifiQrDialog
        dlg = WifiQrDialog(parent=self)
        self._translate_dialog(dlg)
        dlg.exec()

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ekspor Backup", "", "JSON Files (*.json)")
        if path:
            try:
                self.history_manager.export_backup(path)
                QMessageBox.information(self, "Berhasil", f"Backup disimpan ke:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Gagal Ekspor", str(e))

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Impor Backup", "", "JSON Files (*.json)")
        if path:
            try:
                result = self.history_manager.import_backup(path)
                self._refresh_table()
                QMessageBox.information(self, "Berhasil", f"Berhasil diimpor.\nFolder baru: {result.added_count}")
            except Exception as e:
                QMessageBox.critical(self, "Gagal Impor", str(e))
