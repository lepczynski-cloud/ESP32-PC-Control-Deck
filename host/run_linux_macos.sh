#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.9 or newer and run this script again." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
  echo "Python 3.9 or newer is required." >&2
  "$PYTHON_BIN" --version >&2 || true
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating Python virtual environment..."
  if ! "$PYTHON_BIN" -m venv .venv; then
    echo "Could not create host/.venv." >&2
    echo "On Debian or Ubuntu, install python3-venv. On macOS, install a current Python 3." >&2
    exit 1
  fi
fi

REQUIREMENTS_STAMP=".venv/.control-deck-requirements.txt"
NEEDS_INSTALL=0

if [ ! -f "$REQUIREMENTS_STAMP" ] || ! cmp -s requirements.txt "$REQUIREMENTS_STAMP"; then
  NEEDS_INSTALL=1
fi

if ! .venv/bin/python -c 'import importlib.util; raise SystemExit(0 if all(importlib.util.find_spec(name) for name in ("psutil", "serial", "pynput")) else 1)' >/dev/null 2>&1; then
  NEEDS_INSTALL=1
fi

if [ "$NEEDS_INSTALL" -eq 1 ]; then
  echo "Installing Python dependencies..."
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  cp requirements.txt "$REQUIREMENTS_STAMP"
fi

if [ ! -f "config.json" ]; then
  cp config.example.json config.json
  echo "Created host/config.json from the example configuration."
fi

if [ "${1:-}" = "--setup-only" ]; then
  echo "Host bridge setup is complete."
  exit 0
fi

exec .venv/bin/python control_deck_bridge.py "$@"
