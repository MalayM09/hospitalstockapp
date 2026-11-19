"""
Sign-in screen. A correct password goes straight to the dashboard (no
"login successful" message); a wrong one shows an inline error.
"""
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from services.user_service import UserService
from ui.theme import COLORS, fs, icon
from ui.widgets import button, icon_tile, label
from utils import settings


class LoginWindow(QWidget):
    logged_in = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.users = UserService()
        self.setWindowTitle("Lab Stock — Sign in")
        self.setMinimumSize(900, 600)
        self.setObjectName("page")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Brand panel
        brand = QFrame()
        brand.setObjectName("brandPanel")  # selector keeps the gradient off child labels
        brand.setStyleSheet(f"#brandPanel {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                            f"stop:0 {COLORS['accent_pressed']}, stop:1 {COLORS['accent']}); }}")
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(56, 56, 56, 56)
        bl.addStretch()
        bl.addWidget(icon_tile("first-aid-kit-fill", COLORS["accent"], "#FFFFFF", 64))
        bl.addSpacing(18)
        t = label("Lab Stock")
        t.setStyleSheet(f"color:white; font-size:{fs(34)}px; font-weight:700;")
        bl.addWidget(t)
        s = label("Health Center · MSU")
        s.setStyleSheet(f"color:rgba(255,255,255,0.85); font-size:{fs(16)}px;")
        bl.addWidget(s)
        bl.addSpacing(26)
        for ic, text in [("package", "Track every item's stock and history"),
                         ("receipt", "Record purchases and issues in seconds"),
                         ("shield-check", "Automatic backups to a pendrive or Google Drive")]:
            row = QHBoxLayout()
            row.setSpacing(12)
            ico = label()
            ico.setPixmap(icon(ic, "#CCFBF1").pixmap(QSize(20, 20)))
            row.addWidget(ico)
            tx = label(text)
            tx.setStyleSheet(f"color:#E6FFFA; font-size:{fs(14)}px;")
            row.addWidget(tx)
            row.addStretch()
            bl.addLayout(row)
            bl.addSpacing(6)
        bl.addStretch()
        lay.addWidget(brand, 1)

        # Sign-in form
        right = QWidget()
        right.setObjectName("signinPanel")
        right.setStyleSheet(f"#signinPanel {{ background:{COLORS['surface']}; }}")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(64, 0, 64, 0)
        rl.addStretch()
        form = QWidget()
        form.setFixedWidth(340)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(8)
        fl.addWidget(label("Sign in", "pageTitle"))
        fl.addWidget(label("Enter your username and password to continue.", "pageSub"))
        fl.addSpacing(16)
        fl.addWidget(label("Username", "fieldLabel"))
        self.username = QLineEdit(settings.get("last_username") or "")
        self.username.setPlaceholderText("Username")
        fl.addWidget(self.username)
        fl.addSpacing(6)
        fl.addWidget(label("Password", "fieldLabel"))
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle = QAction(icon("eye", COLORS["faint"]), "Show password", self)
        self.toggle.triggered.connect(self._toggle_password)
        self.password.addAction(self.toggle, QLineEdit.ActionPosition.TrailingPosition)
        fl.addWidget(self.password)
        self.error = label("", "fieldError", wrap=True)
        self.error.setMinimumHeight(fs(20))
        fl.addWidget(self.error)
        self.signin = button("Sign in", "primary", callback=self.attempt)
        self.signin.setMinimumHeight(fs(42))
        fl.addWidget(self.signin)
        rl.addWidget(form, alignment=Qt.AlignmentFlag.AlignHCenter)
        rl.addStretch()
        foot = label("Data is saved on this computer and backed up automatically.", "caption")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(foot)
        rl.addSpacing(18)
        lay.addWidget(right, 1)

        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.attempt)
        self.password.textEdited.connect(lambda _t: self.error.setText(""))
        (self.password if self.username.text() else self.username).setFocus()

    def _toggle_password(self):
        hidden = self.password.echoMode() == QLineEdit.EchoMode.Password
        self.password.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        self.toggle.setIcon(icon("eye-slash" if hidden else "eye", COLORS["faint"]))

    def attempt(self):
        user = self.username.text().strip()
        if not user or not self.password.text():
            self.error.setText("Enter your username and password.")
            return
        if self.users.login(user, self.password.text()):
            self.error.setText("")
            settings.set("last_username", user)
            self.logged_in.emit(user)
        else:
            self.error.setText("Incorrect username or password.")
            self.password.selectAll()
            self.password.setFocus()

    def showEvent(self, e):
        super().showEvent(e)
        self.password.clear()
        self.error.setText("")
        (self.password if self.username.text() else self.username).setFocus()
