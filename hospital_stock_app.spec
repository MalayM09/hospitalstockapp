# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build for Hospital Stock Management.
  Windows: single-file dist/HospitalStockApp.exe
  macOS:   dist/HospitalStockApp.app (for previewing)

PyInstaller follows the imports from src/main.py by itself; only data files
(fonts, icon fonts) need listing here.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project = Path(SPECPATH).resolve()
src = project / "src"

a = Analysis(
    [str(src / "main.py")],
    pathex=[str(src)],
    datas=[(str(src / "assets"), "assets")] + collect_data_files("qtawesome"),
    hiddenimports=["qtawesome"],
    excludes=["tkinter", "matplotlib", "pandas", "numpy", "pytest", "PyQt6.QtWebEngineCore",
              "PyQt6.QtMultimedia", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.Qt3DCore"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="HospitalStockApp",
              console=False, upx=False, argv_emulation=False)
    coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="HospitalStockApp")
    app = BUNDLE(coll, name="HospitalStockApp.app", bundle_identifier="org.hospitalstock.app",
                 info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "2.0.0"})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="HospitalStockApp",
              console=False, upx=True, runtime_tmpdir=None, icon=None)
