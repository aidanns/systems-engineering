#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: Virtual environment not found. Run scripts/build.sh first." >&2
    exit 1
fi

if ! command -v d2 &>/dev/null; then
    echo "Error: d2 is not installed or not on PATH." >&2
    echo "Install it from https://d2lang.com/" >&2
    exit 1
fi

OUTPUT_DIR="${1:-$REPO_ROOT/output}"

echo "Generating diagrams to $OUTPUT_DIR..."
"$PYTHON" "$REPO_ROOT/generate.py" "$REPO_ROOT/functional_decomposition/" -o "$OUTPUT_DIR"

echo "Done."
