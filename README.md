# Lab Stock — Hospital Stock Management

Desktop app for a hospital laboratory store: purchases (vendor invoices), stock issues,
stock and issue registers, reports, and automatic backups. Built with Python and PyQt6.

## Features

- **Purchases** — enter a whole vendor invoice (several items), GST as CGST+SGST or IGST,
  invoice round-off, batch and expiry; duplicate-invoice warning; add a new vendor/item on the spot
- **Stock issue** — live balance (including on a back date), "issued to" suggestions,
  stock can never go negative on any date
- **Registers** — Stock register (status filters, item history with running balance),
  Issue register and Bills with date ranges, search, edit, delete, totals
- **Reports** — stock statement (opening/received/issued/closing), purchases by
  month/week/day, vendor-wise, item consumption, GST summary; Excel export and print
- **Backups** — verified backups to this PC, extra folders (pendrive, Google Drive/OneDrive)
  and any plugged-in pendrive; after changes, daily, and on close; tiered retention
  (last 20, daily 60 days, weekly 26 weeks, monthly forever); one-click restore; a new
  or damaged installation offers to restore automatically; daily Excel copies
- **Account** — change password, large-text mode; errors are logged to `logs/app.log`

### Keyboard shortcuts

| Keys | Action | Keys | Action |
|---|---|---|---|
| Ctrl+D | Dashboard | Ctrl+S | Save (purchase / issue) |
| Ctrl+N | New purchase | Esc | Clear the form |
| Ctrl+I | Stock issue | Ctrl+F | Search |
| Ctrl+R | Stock register | F5 | Refresh |
| Ctrl+B | Bills | Enter | Next field / add item |

## Running from source

```bash
pip install -r requirements.txt
python run.py
```

Default login: `admin` / `admin` — change it from the account menu (bottom-left).

## Previewing on a Mac

- **`run_mac.command`** (double-click) — sets up on first run, fills `preview_data/` with
  sample data and starts the app. Option 2 simulates a 1366×768 screen. Delete
  `preview_data/` to reset.
- **`build_mac.command`** (double-click) — builds `dist/HospitalStockApp.app`.

## Building the Windows .exe

GitHub Actions runs the tests and builds `HospitalStockApp.exe` on every push to `main`
and on pull requests (Actions tab → latest run → Artifacts). Locally:

```bash
pip install -r requirements-dev.txt
pyinstaller hospital_stock_app.spec --clean
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Data & backups

All data lives in one folder — `data/` when run from source, `%LOCALAPPDATA%\HospitalStockApp`
on Windows: `hospital.db`, `backups/`, `logs/`, `settings.json`.

**Backups in `backups/` are on the same disk as the database.** Open **Backup & Restore** and
add at least one off-site location (pendrive or Google Drive folder); the dashboard stays red
until you do. Schema changes are applied automatically by `src/models/migrations.py`
(a backup is taken first).

## Project structure

```
src/
  main.py                 startup: crash handler, restore offer, migrations, sign-in
  models/                 migrations.py (schema), seed_data.py (first run only)
  services/               business logic, no UI
    bill_service.py       invoices, edits, invoice round-off
    stock_service.py      stock movements, negative-stock protection, item ledger
    report_service.py     reports + dashboard figures
    backup_service.py     backups, retention, restore;  backup_scheduler.py: when
    export_service.py     Excel exports;  gst.py: tax maths
    master_service.py     items & vendors (item_service.py, vendor_service.py)
  ui/
    theme.py              Clinical Teal design system (colours, font, stylesheet)
    widgets.py            shared components (tables, fields, search combos, toasts…)
    main_window.py        sidebar + pages;  login_window.py;  dialogs.py;  printing.py
    pages/                one file per screen
  assets/fonts/           Inter font (SIL Open Font License)
tests/                    pytest suite (logic, backups, every screen)
tools/demo_data.py        sample data for previews
```
