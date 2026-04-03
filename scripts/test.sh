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

echo "Checking d2 generation (no rendering)..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
for f in "$REPO_ROOT"/functional_decomposition/*.yaml "$REPO_ROOT"/functional_decomposition/*.yml; do
    [ -f "$f" ] || continue
    # Run generate.py but expect it to fail at d2 rendering if d2 is not installed.
    # We just check that the .d2 file is created.
    "$PYTHON" "$REPO_ROOT/generate.py" "$f" -o "$TMPDIR" 2>/dev/null || true
    stem="$(basename "${f%.*}")"
    if [ -f "$TMPDIR/$stem.d2" ]; then
        echo "  OK: $f -> $stem.d2"
    else
        echo "  FAIL: $f (no .d2 output)" >&2
        exit 1
    fi
done

echo "All tests passed."
