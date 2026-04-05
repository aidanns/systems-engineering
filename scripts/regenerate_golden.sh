#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GOLDEN_DIR="$REPO_ROOT/tests/golden"

echo "Regenerating golden files..."
"$REPO_ROOT/.venv/bin/systems-engineering" function "$REPO_ROOT/example/functional_decomposition.yaml" -o "$GOLDEN_DIR"
"$REPO_ROOT/.venv/bin/systems-engineering" product diagram "$REPO_ROOT/example/product_breakdown.yaml" -o "$GOLDEN_DIR"
echo "Golden files regenerated in $GOLDEN_DIR"
