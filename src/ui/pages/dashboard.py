from datetime import date

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from services.report_service import ReportService
from ui.pages.base import Page
from ui.theme import COLORS, icon
from ui.widgets import Card, DataTable, KpiCard, button, icon_tile, label
from utils.formatting import inr, nice_date, qty


class BackupPill(QFrame):
    """Clickable backup status (green / amber / red)."""

    STYLES = {
        "ok": (COLORS["success"], COLORS["success_soft"], "cloud-check"),
        "warn": (COLORS["warning"], COLORS["warning_soft"], "warning-circle"),
        "danger": (COLORS["danger"], COLORS["danger_soft"], "warning-circle"),
    }

    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 7, 14, 7)
        lay.setSpacing(8)
        self.icon = QLabel()
        self.text = QLabel()
        lay.addWidget(self.icon)
        lay.addWidget(self.text)
        self.setMaximumWidth(520)

    def set_status(self, level, text, short):
        fg, bg, ic = self.STYLES[level]
        self.setStyleSheet(f"QFrame {{ background:{bg}; border-radius:8px; }}")
        self.icon.setPixmap(icon(ic, fg).pixmap(QSize(18, 18)))
        self.text.setText(short)
        self.text.setStyleSheet(f"color:{fg}; font-weight:600;")
        self.setToolTip(text + "\n\nClick to open Backup & Restore.")

    def mousePressEvent(self, e):
        self.on_click()


class ActivityRow(QWidget):
    def __init__(self, r):
        super().__init__()
        incoming = r["qty_in"] > 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        if r["qty_in"] < 0:  # correction / reversal
            tile = icon_tile("arrow-counter-clockwise", COLORS["warning"], COLORS["warning_soft"], 30)
        elif incoming:
            tile = icon_tile("arrow-down-left", COLORS["success"], COLORS["success_soft"], 30)
        else:
            tile = icon_tile("arrow-up-right", COLORS["danger"], COLORS["danger_soft"], 30)
        lay.addWidget(tile)
        text = QVBoxLayout()
        text.setSpacing(0)
        name = label(r["item"], "strong")
        text.addWidget(name)
        if r["txn_type"] == "ISSUE":
            sub = f"Issued · {r['remarks'] or 'Lab'}"
        elif r["txn_type"] == "OPENING":
            sub = "Opening stock"
        elif r["qty_in"] < 0:
            sub = "Correction"
        else:
            sub = f"Purchase · {r['vendor'].title()}"
        text.addWidget(label(sub, "caption"))
        lay.addLayout(text, 1)
        right = QVBoxLayout()
        right.setSpacing(0)
        amount = r["qty_in"] - r["qty_out"]
        q = label(f"+{qty(amount)}" if amount > 0 else f"−{qty(-amount)}")
        q.setStyleSheet(f"font-weight:700; color:{COLORS['success'] if amount > 0 else COLORS['danger']};")
        q.setAlignment(Qt.AlignmentFlag.AlignRight)
        d = label(nice_date(r["date"], with_year=False), "caption")
        d.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(q)
        right.addWidget(d)
        lay.addLayout(right)


class DashboardPage(Page):
    nav_key = "dashboard"
    title = "Dashboard"

    def __init__(self, main):
        super().__init__(main)
        self.service = ReportService()

        self.backup_pill = self.header.add_action(BackupPill(lambda: main.navigate("backup")))
        self.header.add_action(button("New purchase", "primary", "plus",
                                      "New purchase (Ctrl+N)", lambda: main.navigate("purchase")))

        kpis = QGridLayout()
        kpis.setSpacing(16)
        self.k_items = KpiCard("package", "Items tracked", COLORS["accent"], COLORS["accent_soft"])
        self.k_low = KpiCard("warning-circle", "Low / out of stock", COLORS["warning"], COLORS["warning_soft"])
        self.k_purchase = KpiCard("currency-inr", "Purchases this month", COLORS["success"], COLORS["success_soft"])
        self.k_issue = KpiCard("export", "Issued this month", COLORS["accent"], COLORS["accent_soft"])
        for i, k in enumerate((self.k_items, self.k_low, self.k_purchase, self.k_issue)):
            kpis.addWidget(k, 0, i)
        self.root.addLayout(kpis)

        row = QHBoxLayout()
        row.setSpacing(16)

        low_card = Card(margins=(18, 16, 18, 8))
        head = QHBoxLayout()
        head.addWidget(label("Low stock", "cardTitle"))
        head.addStretch()
        head.addWidget(button("View stock register →", "link",
                              callback=lambda: main.navigate("stock")))
        low_card.add(head)
        self.low_table = DataTable([("Item", "text"), ("Balance", "int"), ("Status", "status")],
                                   empty_text="All items are well stocked.")
        self.low_table.activated.connect(lambda item_id: main.show_item_ledger(item_id))
        low_card.add(self.low_table, 1)
        row.addWidget(low_card, 3)

        act_card = Card()
        act_card.add(label("Recent activity", "cardTitle"))
        self.activity = QVBoxLayout()
        self.activity.setSpacing(10)
        act_card.add(self.activity)
        act_card.layout_.addStretch()
        row.addWidget(act_card, 2)
        self.root.addLayout(row, 1)

    def refresh(self):
        d = self.service.dashboard()
        self.header.subtitle.setText(f"Stock position as on {date.today():%d %B %Y}")
        self.k_items.set(qty(d["items"]), "items in the item list")
        self.k_low.set(qty(len(d["low"])), f"{d['out_count']} completely out" if d["out_count"] else "none completely out")
        self.k_purchase.set(inr(d["purchase_total"], 0),
                            f"{d['invoice_count']} invoice{'s' if d['invoice_count'] != 1 else ''}")
        self.k_issue.set(f"{qty(d['issued_units'])} units",
                         f"{d['issue_count']} issue entr{'y' if d['issue_count'] == 1 else 'ies'}")

        from services.stock_service import stock_status
        self.low_table.set_rows([(b["name"], b["balance"], stock_status(b["balance"])) for b in d["low"]],
                                ids=[b["id"] for b in d["low"]])

        while self.activity.count():
            w = self.activity.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not d["recent"]:
            self.activity.addWidget(label("No entries yet. Purchases and issues will appear here.", "muted", wrap=True))
        for r in d["recent"][:8]:
            self.activity.addWidget(ActivityRow(r))

        self.refresh_backup_status()

    def refresh_backup_status(self):
        from services.backup_service import BackupService
        from services.db_service import get_db
        s = BackupService(get_db()).status_summary()
        short = {"ok": "Backed up", "warn": "Backup needs attention", "danger": "Backup needed"}[s["level"]]
        if s["level"] == "ok":
            short = s["text"].split("·")[0].replace("Last off-site backup", "Backed up").strip()
        self.backup_pill.set_status(s["level"], s["text"], short)
