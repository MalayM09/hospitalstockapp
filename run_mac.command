#!/bin/bash
# Double-click to preview the app on this Mac.
# Uses SAMPLE data in the preview_data/ folder - nothing here touches real data.
cd "$(dirname "$0")"
source tools/mac_setup.sh || exit 1

echo ""
echo "How should the app open?"
echo "  1) Full screen (this Mac's size)"
echo "  2) Simulate the hospital PC screen (1366 x 768)"
echo "  3) Simulate another size (e.g. 1920x1080, 1600x900, 1280x1024)"
read -p "Choose 1, 2 or 3 [1]: " choice
case "$choice" in
    2) export HOSPITAL_SCREEN=1366x768 ;;
    3) read -p "Screen size (WIDTHxHEIGHT): " size; export HOSPITAL_SCREEN="$size" ;;
    *) unset HOSPITAL_SCREEN ;;
esac

export HOSPITAL_STOCK_DATA_DIR="$PWD/preview_data"
if [ ! -f preview_data/hospital.db ]; then
    echo "Creating sample data..."
    .venv/bin/python tools/demo_data.py
fi

echo "Starting... (login: admin / admin)   To reset sample data, delete the preview_data folder."
.venv/bin/python run.py
