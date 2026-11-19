#!/bin/bash
# Shared by run_mac.command and build_mac.command:
# creates .venv (once) and installs/updates the dependencies.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || return 1

PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$candidate"; break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3.10 or newer is needed. Install it from https://www.python.org/downloads/"
    read -p "Press Enter to close."; return 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "First run: setting up (takes a minute or two)..."
    "$PY" -m venv .venv || { echo "Could not create .venv"; return 1; }
fi
# Re-install only when requirements.txt changed
if [ ! -f .venv/.req_stamp ] || [ requirements.txt -nt .venv/.req_stamp ] || [ requirements-dev.txt -nt .venv/.req_stamp ]; then
    .venv/bin/python -m pip install -q --upgrade pip
    .venv/bin/python -m pip install -q -r requirements-dev.txt || {
        echo "Installing dependencies failed (check the internet connection)."
        read -p "Press Enter to close."; return 1; }
    touch .venv/.req_stamp
fi
