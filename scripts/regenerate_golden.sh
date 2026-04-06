#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/venv.sh"
GOLDEN_DIR="$REPO_ROOT/tests/golden"

echo "Regenerating golden files..."
"$VENV_DIR/bin/systems-engineering" function "$REPO_ROOT/example/functional_decomposition.yaml" -o "$GOLDEN_DIR"
"$VENV_DIR/bin/systems-engineering" product diagram "$REPO_ROOT/example/product_breakdown.yaml" -o "$GOLDEN_DIR"
echo "Golden files regenerated in $GOLDEN_DIR"
