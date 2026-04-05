#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GOLDEN_DIR="$REPO_ROOT/tests/golden"
TMPDIR="$(mktemp -d)"

trap 'rm -rf "$TMPDIR"' EXIT

echo "Regenerating golden files..."

# Generate all output files to temp directory
"$REPO_ROOT/.venv/bin/systems-engineering" function "$REPO_ROOT/functional_decomposition/example.yaml" -o "$TMPDIR"

# Copy text golden files (regenerate from Python to ensure consistent formatting)
"$REPO_ROOT/.venv/bin/python" -c "
from systems_engineering.cli import load_yaml, yaml_to_d2, yaml_to_markdown, yaml_to_csv
from pathlib import Path
data = load_yaml(Path('$REPO_ROOT/functional_decomposition/example.yaml'))
Path('$GOLDEN_DIR/example_functions.d2').write_text(yaml_to_d2(data))
Path('$GOLDEN_DIR/example_functions.md').write_text(yaml_to_markdown(data))
f = Path('$GOLDEN_DIR/example_functions.csv').open('w', newline='')
f.write(yaml_to_csv(data))
f.close()
"

# Copy binary golden files from rendered output
cp "$TMPDIR/example_functions.svg" "$GOLDEN_DIR/example_functions.svg"
cp "$TMPDIR/example_functions.png" "$GOLDEN_DIR/example_functions.png"

echo "Golden files regenerated in $GOLDEN_DIR"
