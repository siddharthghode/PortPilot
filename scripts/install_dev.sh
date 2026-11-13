#!/usr/bin/env bash
# PortPilot Development Installation Script
# Supports: Arch Linux, Ubuntu, Debian, Fedora

set -euo pipefail

echo "=========================================================="
echo "  PortPilot: Linux Port & Process Management Setup"
echo "=========================================================="

# Check Python version
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is not installed." >&2
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]; }; then
    echo "Error: Python 3.12 or newer is required. Detected version: $PYTHON_VERSION" >&2
    exit 1
fi

echo "[1/4] Found Python $PYTHON_VERSION"

# Setup virtual environment
VENV_DIR="${VENV_DIR:-.venv}"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/4] Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "[2/4] Reusing existing virtual environment at $VENV_DIR"
fi

# Activate venv
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "[3/4] Installing dependencies and dev tools..."
pip install --upgrade pip setuptools wheel >/dev/null

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

echo "[4/4] Verifying installation..."
portpilot --version
pytest -q

echo "=========================================================="
echo "  PortPilot successfully installed in development mode!!!!!!"
echo "  Run: source $VENV_DIR/bin/activate"
echo "       portpilot --help"
echo "=========================================================="
