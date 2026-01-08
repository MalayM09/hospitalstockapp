# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Hospital Stock Management App
Builds a single-file Windows executable
"""

import sys
from pathlib import Path

block_cipher = None

# Get the absolute path to the project
project_path = Path(SPECPATH).resolve()
src_path = project_path / 'src'

a = Analysis(
    [str(src_path / 'main.py')],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        # Include any data files if needed
        # (str(project_path / 'data'), 'data'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtPrintSupport',
        'bcrypt',
        'pandas',
        'openpyxl',
        'sqlite3',
        # Service modules
        'services',
        'services.db_service',
        'services.user_service',
        'services.bill_service',
        'services.stock_service',
        'services.item_service',
        'services.vendor_service',
        'services.backup_service',
        # UI modules
        'ui',
        'ui.theme',
        'ui.login_window',
        'ui.dashboard_window',
        'ui.vendor_window',
        'ui.item_window',
        'ui.bill_entry_window',
        'ui.stock_issue_window',
        'ui.stock_receive_window',
        'ui.stock_register_view_window',
        'ui.bill_details_view_window',
        'ui.reports_window',
        'ui.stock_issuance_register_window',
        # Model modules
        'models',
        'models.init_db',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.testing',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HospitalStockApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'icon.ico' here if you have an icon
)
