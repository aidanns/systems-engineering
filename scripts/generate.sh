#!/usr/bin/env bash

# Generate all diagrams from example YAML files to the output directory.

set -euo pipefail

source "$(dirname "$0")/env.sh"
SYSTEMS_ENGINEERING="$VENV_DIR/bin/systems-engineering"

if [ ! -f "$SYSTEMS_ENGINEERING" ]; then
    echo "Error: systems-engineering CLI not found in virtualenv. Run scripts/build.sh first." >&2
    exit 1
fi

if ! command -v d2 &>/dev/null; then
    echo "Error: d2 is not installed or not on PATH." >&2
    echo "Install it from https://d2lang.com/" >&2
    exit 1
fi

OUTPUT_DIR="${1:-$REPO_ROOT/output}"

echo "Generating diagrams to $OUTPUT_DIR..."
"$SYSTEMS_ENGINEERING" function diagram "$REPO_ROOT/example/" -o "$OUTPUT_DIR"
"$SYSTEMS_ENGINEERING" product diagram "$REPO_ROOT/example/" -o "$OUTPUT_DIR"

echo "Regenerating design artefacts..."
"$SYSTEMS_ENGINEERING" function diagram "$REPO_ROOT/design/functional_decomposition.yaml" -o "$REPO_ROOT/design/"
"$SYSTEMS_ENGINEERING" product diagram "$REPO_ROOT/design/product_breakdown.yaml" -o "$REPO_ROOT/design/"

echo "Done."
