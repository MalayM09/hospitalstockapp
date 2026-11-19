from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ui.widgets import PageHeader


class Page(QWidget):
    """
    One screen inside the main window.

    refresh()      reload data (called when shown, and after data changes)
    on_save()      Ctrl+S
    on_escape()    Esc
    focus_search() Ctrl+F
    """
    nav_key = ""
    title = ""
    subtitle = ""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("page")
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(28, 22, 28, 22)
        self.root.setSpacing(16)
        self.header = PageHeader(self.title, self.subtitle)
        self.root.addWidget(self.header)

    def refresh(self):
        pass

    def on_save(self):
        pass

    def on_escape(self):
        pass

    def focus_search(self):
        search = getattr(self, "search", None)
        if search is not None:
            search.setFocus()
            search.selectAll()
