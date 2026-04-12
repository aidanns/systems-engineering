#!/usr/bin/env bash

# Build a wheel and generate a SHA256 checksum file into the given output directory.

set -euo pipefail

source "$(dirname "$0")/env.sh"

OUTDIR="${1:?Usage: build-wheel.sh <output-directory>}"
mkdir -p "$OUTDIR"

"$VENV_DIR/bin/pip" install --quiet build
"$VENV_DIR/bin/python" -m build --wheel --outdir "$OUTDIR" "$REPO_ROOT"

wheel_path="$(ls "$OUTDIR"/*.whl)"
wheel_filename="$(basename "$wheel_path")"
checksum_path="$OUTDIR/${wheel_filename}.sha256"

if command -v sha256sum >/dev/null 2>&1; then
    (cd "$OUTDIR" && sha256sum "$wheel_filename" > "$checksum_path")
else
    (cd "$OUTDIR" && shasum -a 256 "$wheel_filename" > "$checksum_path")
fi

echo "$wheel_filename"
