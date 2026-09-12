#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

if [ ! -f "config.json" ]; then
  cp config.example.json config.json
  echo "Created host/config.json from the example configuration."
fi

exec .venv/bin/python control_deck_bridge.py
