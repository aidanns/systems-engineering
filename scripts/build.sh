#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Creating virtual environment..."
python3 -m venv "$REPO_ROOT/.venv"

echo "Installing package..."
"$REPO_ROOT/.venv/bin/pip" install -e "$REPO_ROOT[test]"

echo "Build complete."
