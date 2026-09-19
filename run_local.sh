#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🛡️  CR-SHIELD PRO: Starting Local Studio Server"
echo "=================================================="

if [ ! -d "venv" ]; then
    echo "[!] Virtualenv not found. Creating..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo "[*] Server URL: http://127.0.0.1:8000"
echo "[*] Open http://127.0.0.1:8000 in your browser to start!"
echo "--------------------------------------------------"

exec ./venv/bin/python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
