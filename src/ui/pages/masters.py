"""Items and Vendors lists."""
from services.item_service import ItemService
from services.master_service import MasterError
from services.stock_service import stock_status
from services.vendor_service import VendorService
from ui.pages.table_page import TablePage
from ui.widgets import alert, button, confirm, toast


class MasterPage(TablePage):
    service_cls = None
    noun = ""

    def __init__(self, main):
        self.service = self.service_cls()
        super().__init__(main)
        self.header.add_action(button(f"Add {self.noun}", "primary", "plus", f"Add a new {self.noun}", self.add))

    def add_actions(self, bar):
        bar.addWidget(button("Rename", None, "pencil-simple", f"Rename the selected {self.noun}",
                             lambda: self.on_activate(self.table.selected_id())))
        bar.addWidget(button("Delete", "danger", "trash", f"Delete the selected {self.noun}", self.delete_selected))

    def add(self):
        from ui.dialogs import NameDialog
        dlg = NameDialog(f"Add {self.noun}", f"{self.noun.title()} name", "", self)
        while dlg.exec():
            try:
                new_id = self.service.add(dlg.value())
            except MasterError as e:
                dlg.set_error(str(e))
                continue
            toast(self, f"{self.noun.title()} added")
            self.refresh()
            self.table.select_id(new_id)
            break

    def on_activate(self, row_id):
        if row_id is None:
            toast(self, f"Select a {self.noun} first", "info")
            return
        from ui.dialogs import NameDialog
        current = self.service.get(row_id)
        dlg = NameDialog(f"Rename {self.noun}", f"{self.noun.title()} name", current["name"], self)
        while dlg.exec():
            try:
                self.service.rename(row_id, dlg.value())
            except MasterError as e:
                dlg.set_error(str(e))
                continue
            toast(self, "Renamed")
            break

    def delete_selected(self):
        row_id = self.table.selected_id()
        if row_id is None:
            toast(self, f"Select a {self.noun} first", "info")
            return
        name = self.service.get(row_id)["name"]
        if not confirm(self, f"Delete {self.noun}?", f"Delete '{name}'?"):
            return
        try:
            self.service.delete(row_id)
        except MasterError as e:
            alert(self, "Cannot delete", str(e))
            return
        toast(self, f"{self.noun.title()} deleted")


class ItemsPage(MasterPage):
    nav_key = "items"
    title = "Items"
    subtitle = "Everything the lab stocks · double-click to rename"
    service_cls = ItemService
    noun = "item"
    columns = [("Item", "text"), ("Balance", "int"), ("Status", "status"), ("Purchase lines", "int")]
    search_placeholder = "Search items…"
    empty_text = "No items match."

    def load(self):
        rows = self.service.get_all_with_stats()
        return ([(r["name"], r["balance"], stock_status(r["balance"]), r["purchases"]) for r in rows],
                [r["id"] for r in rows])


class VendorsPage(MasterPage):
    nav_key = "vendors"
    title = "Vendors"
    subtitle = "Suppliers · double-click to rename"
    service_cls = VendorService
    noun = "vendor"
    columns = [("Vendor", "text"), ("Invoices", "int"), ("Total purchased", "money"), ("Last purchase", "date")]
    search_placeholder = "Search vendors…"
    empty_text = "No vendors match."
    sum_columns = (2,)

    def load(self):
        rows = self.service.get_all_with_stats()
        return ([(r["name"], r["invoices"], r["total"], r["last_purchase"]) for r in rows],
                [r["id"] for r in rows])
