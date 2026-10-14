"""
ui/styles.py - Stylesheet definitions.
"""

BTN_PRIMARY = """
QPushButton {
    background-color: #176b49;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover  { background-color: #0f5136; }
QPushButton:pressed { background-color: #0b402b; }
QPushButton:disabled {
    background-color: #9fcdb2;
    color: #dff3e8;
}
"""

BTN_DANGER = """
QPushButton {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover  { background-color: #dc2626; }
QPushButton:pressed { background-color: #b91c1c; }
"""

BTN_SUCCESS = """
QPushButton {
    background-color: #2c9968;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover  { background-color: #059669; }
QPushButton:pressed { background-color: #047857; }
"""

BTN_NORMAL = """
QPushButton {
    background-color: #edf3ef;
    color: #304037;
    border: 1px solid #cad5cd;
    border-radius: 10px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover  { background-color: #dfe5df; border-color: #86948b; }
QPushButton:pressed { background-color: #cad5cd; }
QPushButton:disabled { background-color: #edf8f1; color: #86948b; }
"""

BTN_SIDEBAR = """
QPushButton {
    background-color: transparent;
    color: #86948b;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
QPushButton:hover  { background-color: #edf8f1; color: #14563a; }
QPushButton:checked { background-color: #edf8f1; color: #14563a; font-weight: 600; }
"""

BTN_TOPBAR_ICON = """
QPushButton {
    background-color: transparent;
    color: #86948b;
    border: none;
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 18px;
}
QPushButton:hover { background-color: #edf8f1; color: #14563a; }
QPushButton:pressed { background-color: #dfe5df; }
"""

MAIN_STYLE = """
/* Reset & Base */
QWidget {
    font-size: 13px;
    color: #1e293b;
    font-family: "Segoe UI", system-ui, sans-serif;
}

QMainWindow {
    background-color: #f5f7f3;
}

/* ── Content Area ─────────────────────── */
QScrollArea, QStackedWidget {
    background-color: transparent;
    border: none;
}

/* ── Inputs ──────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cad5cd;
    border-radius: 10px;
    padding: 7px 11px;
    color: #1e293b;
    selection-background-color: #176b49;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #176b49;
    background-color: #fafcff;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #edf3ef;
    color: #86948b;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #dfe5df;
}

/* ── Checkboxes ───────────────────────── */
QCheckBox { spacing: 6px; color: #304037; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid #cad5cd;
    border-radius: 3px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #176b49;
    border-color: #176b49;
}
QCheckBox::indicator:hover { border-color: #176b49; }

/* ── Default Push Button ─────────────── */
QPushButton {
    background-color: #edf3ef;
    color: #304037;
    border: 1px solid #cad5cd;
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover  { background-color: #dfe5df; border-color: #86948b; }
QPushButton:pressed { background-color: #cad5cd; }
QPushButton:disabled { background-color: #edf8f1; color: #86948b; border-color: #dfe5df; }

/* ── Table / List / Tree ──────────────── */
QTableWidget, QListWidget, QTreeView {
    background-color: #ffffff;
    border: none;
    outline: none;
    gridline-color: #edf3ef;
    selection-background-color: #dff3e8;
    selection-color: #1e293b;
}
QTableWidget::item, QListWidget::item, QTreeView::item {
    padding: 6px 8px;
    border-bottom: 1px solid #edf3ef;
}
QTableWidget::item:hover, QListWidget::item:hover, QTreeView::item:hover {
    background-color: #edf8f1;
}
QTableWidget::item:selected, QListWidget::item:selected, QTreeView::item:selected {
    background-color: #dff3e8;
    color: #1e293b;
}
QHeaderView::section {
    background-color: #edf8f1;
    color: #52635a;
    padding: 8px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #dfe5df;
    border-right: 1px solid #edf3ef;
}
QHeaderView::section:first { padding-left: 16px; }

/* ── ScrollBars ───────────────────────── */
QScrollBar:vertical {
    border: none; background: #edf3ef; width: 7px; border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #cad5cd; min-height: 20px; border-radius: 3px;
}
QScrollBar::handle:vertical:hover { background: #86948b; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    border: none; background: #edf3ef; height: 7px; border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #cad5cd; min-width: 20px; border-radius: 3px;
}
QScrollBar::handle:horizontal:hover { background: #86948b; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ── ToolTip ──────────────────────────── */
QToolTip {
    background-color: #ffffff;
    color: #17211c;
    border: 1px solid #dfe5df;
    border-radius: 10px;
    padding: 5px 8px;
    font-size: 12px;
}

/* ── Dialogs ──────────────────────────── */
QDialog {
    background-color: #f5f7f3;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
    padding: 6px 16px;
}

/* ── GroupBox ─────────────────────────── */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #dfe5df;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    font-size: 12px;
    color: #52635a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    background: #ffffff;
    color: #176b49;
}

/* ── Splitter ─────────────────────────── */
QSplitter::handle {
    background-color: #dfe5df;
    width: 1px;
}

/* ── Status Bar ───────────────────────── */
QStatusBar {
    background-color: #ffffff;
    color: #86948b;
    font-size: 11px;
    border-top: 1px solid #dfe5df;
}
QStatusBar::item { border: none; }

/* ── Menu ─────────────────────────────── */
QMenuBar {
    background-color: #ffffff;
    color: #86948b;
    padding: 2px;
    border-bottom: 1px solid #dfe5df;
}
QMenuBar::item {
    padding: 5px 12px;
    border-radius: 10px;
}
QMenuBar::item:selected, QMenuBar::item:pressed {
    background-color: #edf8f1;
    color: #14563a;
}
QMenu {
    background-color: #ffffff;
    color: #17211c;
    border: 1px solid #dfe5df;
    border-radius: 10px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px 8px 14px;
    border-radius: 10px;
}
QMenu::item:selected {
    background-color: #176b49;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #dfe5df;
    margin: 4px 8px;
}
QMenu::indicator { width: 14px; height: 14px; }
"""

MODERN_STYLE = MAIN_STYLE

def theme_stylesheet(theme: str) -> str:
    """Return the shared application stylesheet for light, dark, or system mode."""
    if _resolve_theme(theme) != "dark":
        return MAIN_STYLE
    return _darken_stylesheet(MAIN_STYLE)

def _resolve_theme(theme: str) -> str:
    if theme != "system":
        return theme if theme in {"light", "dark"} else "light"
    if __import__("os").name == "nt":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "dark"
        except OSError:
            pass
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette
    app = QApplication.instance()
    if app and app.palette().color(QPalette.ColorRole.Window).lightness() < 128:
        return "dark"
    return "light"

def _darken_stylesheet(stylesheet: str) -> str:
    import re

    colors = {
        "#ffffff": "#1e1e1e", "#fafcff": "#262626", "#f5f7f3": "#141414",
        "#f6f9f7": "#181818", "#edf8f1": "#292929", "#edf3ef": "#262626",
        "#f3f7f4": "#262626", "#f9fcfa": "#2c2c2c", "#e7f4ec": "#303030",
        "#dff3e8": "#353535", "#dfe5df": "#3c3c3c", "#dfe8e1": "#3c3c3c",
        "#cad5cd": "#555555", "#cbd8cf": "#555555", "#86948b": "#a0a0a0",
        "#87948c": "#a0a0a0", "#68756e": "#b0b0b0", "#52635a": "#c2c2c2",
        "#4a5568": "#c2c2c2", "#edf2f7": "#262626", "#ecfdf5": "#292929",
        "#304037": "#d4dfd7", "#1e293b": "#e4ede7", "#17211c": "#e4ede7",
        "#176b49": "#16835c", "#14563a": "#11734f", "#065f46": "#11734f", "#2c9968": "#14734f",
    }
    replacements = {key: f"__ITSHARE_COLOR_{index}__" for index, key in enumerate(colors)}
    themed = stylesheet

    themed = re.sub(r"(background-color\s*:\s*)#9fcdb2", r"\1#383838", themed, flags=re.IGNORECASE)
    themed = re.sub(r"(?<![-\w])color\s*:\s*#dff3e8", r"color: #a8a8a8", themed, flags=re.IGNORECASE)
    for original, token in replacements.items():
        themed = re.sub(re.escape(original), token, themed, flags=re.IGNORECASE)
    for original, token in replacements.items():
        themed = themed.replace(token, colors[original])
    return themed

def apply_theme(widget, theme: str) -> None:
    """Apply theme to shared QSS and translate existing inline widget colors."""
    from PySide6.QtWidgets import QWidget

    resolved_theme = _resolve_theme(theme)
    widget.setProperty("_itshare_theme", theme)
    widgets = [widget, *widget.findChildren(QWidget)]
    for child in widgets:
        current = child.styleSheet()
        original = child.property("_itshare_original_stylesheet")
        applied = child.property("_itshare_applied_stylesheet")
        if original is None or current != applied:
            original = current
            child.setProperty("_itshare_original_stylesheet", original)
        if resolved_theme == "dark":
            themed = _darken_stylesheet(original or "")
        else:
            themed = original or ""
        child.setStyleSheet(themed)
        child.setProperty("_itshare_applied_stylesheet", themed)
    widget.setStyleSheet(theme_stylesheet(theme))
