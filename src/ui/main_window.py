"""
Main window: sidebar navigation + one page at a time.

Pages are created the first time they are opened. When data changes anywhere
(save, edit, delete, restore), the visible page refreshes immediately and the
others refresh the next time they are shown — so every screen is always current.
"""
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QMenu, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from ui.theme import COLORS, icon, set_large_text
from ui.widgets import icon_tile, label, toast
from utils import settings

NAV = [
    ("OVERVIEW", [("dashboard", "Dashboard", "squares-four", "Ctrl+D")]),
    ("TRANSACTIONS", [("purchase", "Purchases", "shopping-cart-simple", "Ctrl+N"),
                      ("issue", "Stock Issue", "export", "Ctrl+I")]),
    ("REGISTERS", [("stock", "Stock Register", "package", "Ctrl+R"),
                   ("issues", "Issue Register", "clipboard-text", None),
                   ("bills", "Bills", "receipt", "Ctrl+B")]),
    ("MASTERS", [("items", "Items", "tag", None), ("vendors", "Vendors", "truck", None)]),
    ("SYSTEM", [("reports", "Reports", "chart-bar", None), ("backup", "Backup & Restore", "shield-check", None)]),
]


def _page_class(key):
    from ui.pages.backup import BackupPage
    from ui.pages.dashboard import DashboardPage
    from ui.pages.issue import IssuePage
    from ui.pages.masters import ItemsPage, VendorsPage
    from ui.pages.purchase import PurchasePage
    from ui.pages.registers import BillsPage, IssueRegisterPage, StockRegisterPage
    from ui.pages.reports import ReportsPage
    return {
        "dashboard": DashboardPage, "purchase": PurchasePage, "issue": IssuePage, "stock": StockRegisterPage,
        "issues": IssueRegisterPage, "bills": BillsPage, "items": ItemsPage, "vendors": VendorsPage,
        "reports": ReportsPage, "backup": BackupPage,
    }[key]


class MainWindow(QMainWindow):
    logged_out = pyqtSignal()

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Lab Stock — Health Center, MSU")
        self.setMinimumSize(1024, 640)
        self.pages, self.stale, self.nav_buttons = {}, set(), {}
        self.current = None

        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        for sc, fn in [("Ctrl+S", lambda: self.current and self.current.on_save()),
                       ("Esc", lambda: self.current and self.current.on_escape()),
                       ("Ctrl+F", lambda: self.current and self.current.focus_search()),
                       ("F5", lambda: self.current and self.current.refresh())]:
            QShortcut(QKeySequence(sc), self, activated=fn)

        from services.backup_scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            sched.data_changed.connect(self.on_data_changed)
            sched.status_changed.connect(self.on_backup_status)

        self.navigate("dashboard")

    # ---- sidebar -----------------------------------------------------------------

    def _sidebar(self):
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(232)
        v = QVBoxLayout(sb)
        v.setContentsMargins(14, 18, 14, 14)
        v.setSpacing(2)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(icon_tile("first-aid-kit-fill", "#FFFFFF", COLORS["accent"], 36))
        names = QVBoxLayout()
        names.setSpacing(0)
        b = label("Lab Stock")
        b.setObjectName("brand")
        s = label("Health Center · MSU")
        s.setObjectName("brandSub")
        names.addWidget(b)
        names.addWidget(s)
        brand.addLayout(names)
        brand.addStretch()
        v.addLayout(brand)
        v.addSpacing(8)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for title, entries in NAV:
            g = label(title)
            g.setObjectName("navGroup")
            v.addWidget(g)
            for key, text, ic, shortcut in entries:
                btn = QPushButton("  " + text.replace("&", "&&"))
                btn.setObjectName("nav")
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setIcon(icon(ic, "#4B5563", active_color=COLORS["accent"]))
                btn.setIconSize(QSize(18, 18))
                if shortcut:
                    btn.setToolTip(f"{text}  ({shortcut})")
                    QShortcut(QKeySequence(shortcut), self, activated=lambda k=key: self.navigate(k))
                btn.clicked.connect(lambda _c, k=key: self.navigate(k))
                group.addButton(btn)
                self.nav_buttons[key] = (btn, ic)
                v.addWidget(btn)
        v.addStretch()

        self.user_btn = QPushButton(f"  {self.username}")
        self.user_btn.setObjectName("userChip")
        self.user_btn.setIcon(icon("user-circle", COLORS["text"]))
        self.user_btn.setIconSize(QSize(24, 24))
        self.user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_btn.setToolTip("Account and settings")
        self.user_btn.clicked.connect(self._user_menu)
        v.addWidget(self.user_btn)
        return sb

    def _user_menu(self):
        menu = QMenu(self)
        menu.addAction(icon("key"), "Change password…", self.change_password)
        large = menu.addAction(icon("text-aa"), "Large text")
        large.setCheckable(True)
        large.setChecked(bool(settings.get("large_text")))
        large.toggled.connect(self.toggle_large_text)
        menu.addSeparator()
        menu.addAction(icon("sign-out"), "Log out", self.logout)
        # Open upwards, just above the user button
        pos = self.user_btn.mapToGlobal(self.user_btn.rect().topLeft())
        pos.setY(pos.y() - menu.sizeHint().height())
        menu.exec(pos)

    # ---- navigation --------------------------------------------------------------

    def navigate(self, key):
        page = self.pages.get(key)
        if page is None:
            page = _page_class(key)(self)
            self.pages[key] = page
            self.stack.addWidget(page)
            self.stale.add(key)
        btn, _ = self.nav_buttons[key]
        btn.setChecked(True)
        self.stack.setCurrentWidget(page)
        self.current = page
        if key in self.stale:
            self.stale.discard(key)
            page.refresh()

    def on_data_changed(self):
        self.stale.update(self.pages.keys())
        if self.current is not None:
            self.stale.discard(self.current.nav_key)
            self.current.refresh()

    def on_backup_status(self):
        dash = self.pages.get("dashboard")
        if dash is not None:
            dash.refresh_backup_status()
        if self.current is not None and self.current.nav_key == "backup":
            self.current.refresh()

    def show_item_ledger(self, item_id):
        from ui.dialogs import ItemLedgerDialog
        ItemLedgerDialog(item_id, self).exec()

    # ---- account -----------------------------------------------------------------

    def change_password(self):
        from ui.dialogs import ChangePasswordDialog
        if ChangePasswordDialog(self.username, self).exec():
            toast(self, "Password changed")

    def toggle_large_text(self, enabled):
        set_large_text(QApplication.instance(), enabled)
        # Rebuild pages so fixed sizes pick up the new text size
        current = self.current.nav_key if self.current else "dashboard"
        for page in self.pages.values():
            self.stack.removeWidget(page)
            page.deleteLater()
        self.pages.clear()
        self.navigate(current)

    def logout(self):
        self.logged_out.emit()
        self.close()
