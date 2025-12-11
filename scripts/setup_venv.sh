#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python3}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR=${VENV_DIR:-"$SCRIPT_DIR/../../venv_python_CodeneAria"}

echo "Creating virtual environment at '$VENV_DIR' using '$PYTHON'"
"$PYTHON" -m venv "$VENV_DIR"

echo "Activating virtual environment"
. "$VENV_DIR/bin/activate"

echo "Upgrading pip, setuptools, wheel"
python -m pip install --upgrade pip setuptools wheel

echo "Installing runtime dependencies"
pip install --no-input requests Flask simpleaudio pytest pyyaml

echo "Setup complete. Activate environment with: source $VENV_DIR/bin/activate"
