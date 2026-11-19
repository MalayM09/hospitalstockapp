# Hospital Stock Management System

A desktop application for managing hospital/lab stock inventory, built with Python and PyQt6.

## Features

- **Secure Login** - Password-protected access with bcrypt hashing
- **Vendor Management** - Add, edit, delete vendors
- **Item Management** - Manage inventory items
- **Purchase Entry** - Record purchases with automatic tax calculation
- **Stock Issue** - Issue stock with balance tracking
- **Stock Register** - View current stock levels with search/filter
- **Bill Details** - View, edit, delete purchase records
- **Reports** - Daily, weekly, monthly, and vendor-wise reports
- **Print & Export** - Print reports or export to Excel
- **Backup & Restore** - Verified backups to this PC, extra folders (second drive,
  Google Drive / OneDrive folder) and any plugged-in USB pendrive; after changes, daily,
  and on close. Tiered retention (last 20, daily 60 days, weekly 26 weeks, monthly forever).
  One-click restore, plus automatic restore offer on a new/damaged installation.
- **Excel copies** - Daily full-data Excel export and a monthly stock statement saved
  with every backup destination
- **Error log** - Unexpected errors are shown and written to `logs/app.log`

## Data & Backups

All data lives in one folder (`data/` in development; `%LOCALAPPDATA%\HospitalStockApp`
on Windows when packaged): `hospital.db`, `backups/`, `logs/`, `settings.json`.

**Important:** backups in `backups/` are on the same disk as the database. Open
**Backup & Restore** and add at least one off-site location (pendrive or Google Drive
folder). The dashboard shows a red warning until you do.

Schema changes are applied automatically by `src/models/migrations.py`
(a backup is taken first).

## Installation (For Development)

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/MalayM09/hospitalstockapp.git
cd hospitalstockapp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python run.py
```

### Default Login
- **Username:** `admin`
- **Password:** `admin`

## Download Pre-built Executable

Go to the [Actions tab](https://github.com/MalayM09/hospitalstockapp/actions) on GitHub, click on the latest successful build, and download the executable from the Artifacts section.

- **Windows:** Download `HospitalStockApp-Windows`
- **Mac:** Download `HospitalStockApp-Mac`

## Project Structure

```
hospitalstockapp/
├── run.py                    # Entry point
├── requirements.txt          # Python dependencies
├── hospital_stock_app.spec   # PyInstaller configuration
├── src/
│   ├── main.py               # Main application
│   ├── models/
│   │   └── init_db.py        # Database schema
│   ├── services/
│   │   ├── db_service.py     # Database operations
│   │   ├── backup_service.py # Auto-backup functionality
│   │   ├── bill_service.py   # Bill management
│   │   ├── stock_service.py  # Stock operations
│   │   ├── item_service.py   # Item CRUD
│   │   ├── vendor_service.py # Vendor CRUD
│   │   └── user_service.py   # Authentication
│   └── ui/
│       ├── theme.py          # Application styling
│       ├── login_window.py   # Login screen
│       ├── dashboard_window.py
│       └── ...               # Other UI windows
└── data/
    ├── hospital.db           # SQLite database
    └── backups/              # Automatic backups
```

## Building Executable Locally

```bash
pip install pyinstaller
pyinstaller hospital_stock_app.spec --clean
```

The executable will be created in the `dist/` folder.

## License

This project is for personal/hospital use.

## Author

Created by MalayM09
