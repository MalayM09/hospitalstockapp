"""
Clinical Teal design system.

One place for colours, font, sizes and the global stylesheet. Screens use
object names / properties (e.g. QPushButton[variant="primary"]) instead of
inline styles, so the whole app stays consistent.
"""
import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette

log = logging.getLogger(__name__)

COLORS = {
    "bg": "#F6F8FA",
    "surface": "#FFFFFF",
    "border": "#E5E7EB",
    "border_strong": "#D1D5DB",
    "text": "#111827",
    "muted": "#6B7280",
    "faint": "#9CA3AF",
    "accent": "#0F766E",
    "accent_hover": "#115E59",
    "accent_pressed": "#134E4A",
    "accent_soft": "#E6F4F1",
    "success": "#15803D",
    "success_soft": "#DCFCE7",
    "warning": "#B45309",
    "warning_soft": "#FEF3C7",
    "danger": "#B91C1C",
    "danger_hover": "#991B1B",
    "danger_soft": "#FEE2E2",
    "row_hover": "#F3F7F6",
}

FONT_FAMILY = "Inter"
RADIUS = 8
_text_scale = 1.0


def assets_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "assets"


def load_fonts():
    global FONT_FAMILY
    loaded = False
    for f in sorted((assets_dir() / "fonts").glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(f)) >= 0:
            loaded = True
    if not loaded:
        log.warning("Bundled Inter font not found; using system font")
        FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else ""


def fs(base):
    """Font size in px, scaled for the 'Large text' setting."""
    return round(base * _text_scale)


def icon(name, color=None, active_color=None):
    """Phosphor line icon, e.g. icon('package'). Use 'name-fill' / 'name-bold' for variants."""
    import qtawesome as qta
    opts = {"color": color or COLORS["text"]}
    if active_color:
        opts["color_active"] = active_color
    return qta.icon(f"ph.{name}", **opts)


def _icon_file(name, color, size=32):
    """Render an icon to a PNG (stylesheets need image files, e.g. dropdown arrows)."""
    from utils.db_path import get_app_data_dir
    folder = get_app_data_dir() / "cache" / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}_{color.strip('#')}_{size}.png"
    if not path.exists():
        from PyQt6.QtCore import QSize
        icon(name, color).pixmap(QSize(size, size)).save(str(path))
    return path.as_posix()


def stylesheet():
    c = COLORS
    r = RADIUS
    chevron = _icon_file("caret-down", c["muted"])
    calendar = _icon_file("calendar-blank", c["muted"])
    check = _icon_file("check-bold", "#FFFFFF")
    up = _icon_file("caret-up", c["muted"])
    return f"""
    * {{ font-family: '{FONT_FAMILY}'; }}
    QWidget {{ font-size: {fs(13)}px; color: {c['text']}; }}
    QMainWindow, #page {{ background: {c['bg']}; }}
    QDialog {{ background: {c['surface']}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{ background: #111827; color: white; border: none; padding: 6px 8px; border-radius: 6px; }}

    /* ---- typography ---- */
    QLabel[role="pageTitle"] {{ font-size: {fs(22)}px; font-weight: 700; }}
    QLabel[role="pageSub"], QLabel[role="muted"] {{ color: {c['muted']}; }}
    QLabel[role="cardTitle"] {{ font-size: {fs(15)}px; font-weight: 600; }}
    QLabel[role="section"] {{ color: {c['muted']}; font-size: {fs(11)}px; font-weight: 700; letter-spacing: 0.6px; }}
    QLabel[role="fieldLabel"] {{ font-size: {fs(12)}px; font-weight: 600; }}
    QLabel[role="fieldError"] {{ color: {c['danger']}; font-size: {fs(12)}px; }}
    QLabel[role="kpiLabel"] {{ color: {c['muted']}; font-size: {fs(12)}px; font-weight: 500; }}
    QLabel[role="kpiValue"] {{ font-size: {fs(24)}px; font-weight: 700; }}
    QLabel[role="caption"] {{ color: {c['muted']}; font-size: {fs(12)}px; }}
    QLabel[role="bigNumber"] {{ font-size: {fs(24)}px; font-weight: 700; color: {c['accent']}; }}
    QLabel[role="strong"] {{ font-weight: 600; }}

    /* ---- cards ---- */
    QFrame[role="card"] {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {r + 2}px; }}
    QFrame[role="divider"] {{ background: {c['border']}; max-height: 1px; min-height: 1px; border: none; }}

    /* ---- buttons ---- */
    QPushButton {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border_strong']};
                   border-radius: {r}px; padding: 8px 14px; font-weight: 600; }}
    QPushButton:hover {{ background: {c['bg']}; border-color: {c['faint']}; }}
    QPushButton:pressed {{ background: {c['border']}; }}
    QPushButton:disabled {{ color: {c['faint']}; background: {c['bg']}; border-color: {c['border']}; }}
    QPushButton:focus {{ border-color: {c['accent']}; }}
    QPushButton[variant="primary"] {{ background: {c['accent']}; color: white; border: 1px solid {c['accent']}; }}
    QPushButton[variant="primary"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
    QPushButton[variant="primary"]:pressed {{ background: {c['accent_pressed']}; }}
    QPushButton[variant="primary"]:disabled {{ background: #9CC9C3; border-color: #9CC9C3; color: white; }}
    QPushButton[variant="danger"] {{ background: {c['surface']}; color: {c['danger']}; border-color: #F3B4B4; }}
    QPushButton[variant="danger"]:hover {{ background: {c['danger_soft']}; }}
    QPushButton[variant="dangerSolid"] {{ background: {c['danger']}; color: white; border-color: {c['danger']}; }}
    QPushButton[variant="dangerSolid"]:hover {{ background: {c['danger_hover']}; }}
    QPushButton[variant="link"] {{ background: transparent; border: none; color: {c['accent']}; padding: 2px 4px; }}
    QPushButton[variant="link"]:hover {{ text-decoration: underline; }}
    QPushButton[variant="ghost"] {{ background: transparent; border: none; padding: 6px; }}
    QPushButton[variant="ghost"]:hover {{ background: {c['bg']}; }}
    QPushButton[variant="segment"] {{ border-radius: 0; padding: 7px 12px; font-weight: 500; }}
    QPushButton[variant="segment"]:checked {{ background: {c['accent_soft']}; color: {c['accent']};
                                              border-color: {c['accent']}; font-weight: 600; }}

    /* ---- inputs ---- */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QTimeEdit, QPlainTextEdit {{
        background: {c['surface']}; border: 1px solid {c['border_strong']}; border-radius: {r}px;
        padding: 7px 10px; selection-background-color: {c['accent']}; selection-color: white;
        min-height: {fs(38) - 16}px; }}  /* 38px total with padding + border, same as uniform_height() */
    QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QTimeEdit:hover {{ border-color: {c['faint']}; }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {c['accent']}; background: #FCFEFE; }}
    QLineEdit[invalid="true"], QComboBox[invalid="true"], QDateEdit[invalid="true"] {{ border: 1px solid {c['danger']}; }}
    QLineEdit:read-only {{ background: {c['bg']}; color: {c['muted']}; }}
    QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{ background: {c['bg']}; color: {c['faint']}; }}
    QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{ border: none; width: 28px; }}
    QComboBox::down-arrow {{ image: url({chevron}); width: 14px; height: 14px; }}
    QDateEdit::down-arrow {{ image: url({calendar}); width: 15px; height: 15px; }}
    QTimeEdit::up-button, QTimeEdit::down-button, QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}
    QTimeEdit::up-arrow, QSpinBox::up-arrow {{ image: url({up}); width: 10px; height: 10px; }}
    QTimeEdit::down-arrow, QSpinBox::down-arrow {{ image: url({chevron}); width: 10px; height: 10px; }}
    QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 6px;
        padding: 4px; outline: 0; selection-background-color: {c['accent_soft']}; selection-color: {c['accent']}; }}
    QComboBox QAbstractItemView::item {{ min-height: {fs(28)}px; padding: 0 8px; }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {c['border_strong']};
                            background: {c['surface']}; }}
    QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; image: url({check}); }}

    /* ---- calendar popup ---- */
    QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {c['surface']}; padding: 4px; }}
    QCalendarWidget QToolButton {{ color: {c['text']}; background: transparent; border: none; padding: 4px 8px;
                                   font-weight: 600; border-radius: 6px; }}
    QCalendarWidget QToolButton:hover {{ background: {c['accent_soft']}; }}
    QCalendarWidget QAbstractItemView {{ selection-background-color: {c['accent']}; selection-color: white;
                                         outline: 0; background: {c['surface']}; }}

    /* ---- tables ---- */
    QTableView {{ background: {c['surface']}; border: none; gridline-color: {c['border']};
                  selection-background-color: {c['accent_soft']}; selection-color: {c['text']}; outline: 0; }}
    QTableView::item {{ padding: 0 8px; border-bottom: 1px solid {c['border']}; }}
    QTableView::item:hover {{ background: {c['row_hover']}; }}
    QTableView::item:selected {{ background: {c['accent_soft']}; color: {c['text']}; }}
    QHeaderView {{ background: {c['surface']}; border: none; }}
    QHeaderView::section {{ background: {c['surface']}; color: {c['muted']}; font-size: {fs(12)}px; font-weight: 600;
        border: none; border-bottom: 1px solid {c['border']}; padding: 8px; }}
    QHeaderView::section:hover {{ color: {c['text']}; }}
    QTableCornerButton::section {{ background: {c['surface']}; border: none; }}

    /* ---- scrollbars ---- */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['faint']}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {c['border_strong']}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    /* ---- sidebar ---- */
    #sidebar {{ background: {c['surface']}; border-right: 1px solid {c['border']}; }}
    QLabel#brand {{ font-size: {fs(15)}px; font-weight: 700; }}
    QLabel#brandSub {{ color: {c['faint']}; font-size: {fs(11)}px; }}
    QLabel#navGroup {{ color: {c['faint']}; font-size: {fs(10)}px; font-weight: 700; letter-spacing: 0.8px;
                       padding: 12px 12px 3px 12px; }}
    QPushButton#nav {{ text-align: left; background: transparent; border: none; border-radius: {r}px;
                       padding: 8px 12px; color: #374151; font-weight: 500; }}
    QPushButton#nav:hover {{ background: {c['bg']}; }}
    QPushButton#nav:checked {{ background: {c['accent_soft']}; color: {c['accent']}; font-weight: 600; }}
    QPushButton#userChip {{ text-align: left; background: transparent; border: none; border-radius: {r}px;
                            padding: 8px 10px; font-weight: 600; }}
    QPushButton#userChip:hover {{ background: {c['bg']}; }}

    /* ---- menus & dialogs ---- */
    QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 6px; }}
    QMenu::item {{ padding: 8px 18px 8px 12px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {c['accent_soft']}; color: {c['accent']}; }}
    QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 6px; }}
    QMessageBox {{ background: {c['surface']}; }}
    QMessageBox QLabel {{ font-size: {fs(13)}px; }}
    QMessageBox QPushButton {{ min-width: 84px; }}
    QListWidget {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {r}px; outline: 0; padding: 4px; }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {c['accent_soft']}; color: {c['text']}; }}
    QListWidget::item:hover {{ background: {c['row_hover']}; }}
    """


def apply_theme(app):
    """Fonts, palette and stylesheet for the whole application."""
    global _text_scale
    from utils import settings
    _text_scale = 1.15 if settings.get("large_text") else 1.0

    app.setStyle("Fusion")  # same look on Windows and macOS
    load_fonts()
    font = QFont(FONT_FAMILY) if FONT_FAMILY else app.font()
    font.setPixelSize(fs(13))
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(COLORS["surface"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#111827"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet())
    app.setWindowIcon(app_icon())


def app_icon():
    import qtawesome as qta
    return qta.icon("ph.first-aid-kit-fill", color=COLORS["accent"])


def set_large_text(app, enabled):
    from utils import settings
    settings.set("large_text", bool(enabled))
    apply_theme(app)
