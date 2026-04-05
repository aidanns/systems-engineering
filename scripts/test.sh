#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: Virtual environment not found. Run scripts/build.sh first." >&2
    exit 1
fi

echo "Checking YAML files parse correctly..."
for f in "$REPO_ROOT"/functional_decomposition/*.yaml "$REPO_ROOT"/functional_decomposition/*.yml; do
    [ -f "$f" ] || continue
    "$PYTHON" -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $f" || { echo "  FAIL: $f"; exit 1; }
done

echo "Checking file generation..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
for f in "$REPO_ROOT"/functional_decomposition/*.yaml "$REPO_ROOT"/functional_decomposition/*.yml; do
    [ -f "$f" ] || continue
    # Run generate.py — rendering may fail if d2 is not installed, but we still
    # check whichever output files were created.
    "$PYTHON" "$REPO_ROOT/generate.py" function "$f" -o "$TMPDIR" 2>/dev/null || true
    stem="$(basename "${f%.*}")"
    for ext in d2 svg png md csv; do
        if [ -f "$TMPDIR/$stem.$ext" ]; then
            echo "  OK: $f -> $stem.$ext"
        else
            echo "  FAIL: $f (no .$ext output)" >&2
            exit 1
        fi
    done
done

echo "All tests passed."
