#!/usr/bin/env bash

# Regenerate golden files in tests/golden/ from current CLI output.

set -euo pipefail

source "$(dirname "$0")/venv.sh"
GOLDEN_DIR="$REPO_ROOT/tests/golden"

echo "Regenerating golden files..."
"$VENV_DIR/bin/systems-engineering" function "$REPO_ROOT/example/functional_decomposition.yaml" -o "$GOLDEN_DIR"
"$VENV_DIR/bin/systems-engineering" product diagram "$REPO_ROOT/example/product_breakdown.yaml" -o "$GOLDEN_DIR"

# Strip d2 version from SVG files so golden comparisons are version-independent
for svg in "$GOLDEN_DIR"/*.svg; do
    sed 's/ data-d2-version="[^"]*"//' "$svg" > "$svg.tmp" && mv "$svg.tmp" "$svg"
done

echo "Golden files regenerated in $GOLDEN_DIR"
