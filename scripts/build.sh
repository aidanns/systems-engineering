#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/venv.sh"

echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing package..."
"$VENV_DIR/bin/pip" install -e "$REPO_ROOT[test]"

echo "Build complete."
