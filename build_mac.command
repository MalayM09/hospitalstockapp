#!/bin/bash
# Double-click to build HospitalStockApp.app for this Mac (same build process as
# the Windows .exe). The finished app is in the dist/ folder.
cd "$(dirname "$0")"
source tools/mac_setup.sh || exit 1

echo "Building HospitalStockApp.app (takes 1-3 minutes)..."
rm -rf build dist
.venv/bin/pyinstaller hospital_stock_app.spec --clean --noconfirm --log-level WARN || {
    read -p "Build failed. Press Enter to close."; exit 1; }

# The .app keeps its data in ~/Library/Application Support/HospitalStockApp.
# Fill it with sample data the first time so the screens aren't empty.
APPDATA="$HOME/Library/Application Support/HospitalStockApp"
if [ ! -f "$APPDATA/hospital.db" ]; then
    echo "Adding sample data for the Mac app..."
    HOSPITAL_STOCK_DATA_DIR="$APPDATA" .venv/bin/python tools/demo_data.py
fi

echo ""
echo "Done: dist/HospitalStockApp.app   (login: admin / admin)"
open dist
read -p "Press Enter to close."
