#!/usr/bin/env bash

# Run all tests: YAML validation, file generation checks, and pytest.

set -euo pipefail

source "$(dirname "$0")/env.sh"
SYSTEMS_ENGINEERING="$VENV_DIR/bin/systems-engineering"

if [ ! -f "$SYSTEMS_ENGINEERING" ]; then
    echo "Error: systems-engineering CLI not found in virtualenv. Run scripts/build.sh first." >&2
    exit 1
fi

PYTHON="$VENV_DIR/bin/python"

echo "Checking YAML files parse correctly..."
f="$REPO_ROOT/example/functional_decomposition.yaml"
"$PYTHON" -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $f" || { echo "  FAIL: $f"; exit 1; }

echo "Checking product breakdown YAML files parse correctly..."
f="$REPO_ROOT/example/product_breakdown.yaml"
"$PYTHON" -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $f" || { echo "  FAIL: $f"; exit 1; }

echo "Checking product verify..."
"$SYSTEMS_ENGINEERING" product verify \
    -p "$REPO_ROOT/example/product_breakdown.yaml" \
    -f "$REPO_ROOT/example/functional_decomposition.yaml"

echo "Checking design product verify..."
"$SYSTEMS_ENGINEERING" product verify \
    -p "$REPO_ROOT/design/product_breakdown.yaml" \
    -f "$REPO_ROOT/design/functions.yaml"

echo "Checking file generation..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
f="$REPO_ROOT/example/functional_decomposition.yaml"
"$SYSTEMS_ENGINEERING" function "$f" -o "$TMPDIR" 2>/dev/null || true
stem="$(basename "${f%.*}")"
for ext in d2 svg png md csv; do
    output_file="${stem}.$ext"
    if [ -f "$TMPDIR/$output_file" ]; then
        echo "  OK: $f -> $output_file"
    else
        echo "  FAIL: $f (no $output_file output)" >&2
        exit 1
    fi
done
# Check that CSV row count matches the number of functions in the YAML (+1 for root).
csv_file="${stem}.csv"
csv_rows=$(( $(wc -l < "$TMPDIR/$csv_file") - 1 ))  # subtract header
yaml_functions=$(yq '[.functions // [] | .. | select(has("name")) | .name] | length' "$f")
expected_rows=$(( yaml_functions + 1 ))  # +1 for root node row
if [ "$csv_rows" -eq "$expected_rows" ]; then
    echo "  OK: $f -> $csv_file has $csv_rows data rows matching $yaml_functions functions + 1 root"
else
    echo "  FAIL: $f -> $csv_file has $csv_rows data rows but expected $expected_rows ($yaml_functions functions + 1 root)" >&2
    exit 1
fi

echo "Checking product diagram file generation..."
f="$REPO_ROOT/example/product_breakdown.yaml"
"$SYSTEMS_ENGINEERING" product diagram "$f" -o "$TMPDIR" 2>/dev/null || true
stem="$(basename "${f%.*}")"
for ext in d2 svg png md csv; do
    output_file="${stem}.$ext"
    if [ -f "$TMPDIR/$output_file" ]; then
        echo "  OK: $f -> $output_file"
    else
        echo "  FAIL: $f (no $output_file output)" >&2
        exit 1
    fi
done
# Check that CSV row count matches components + CIs + root.
csv_file="${stem}.csv"
csv_rows=$(( $(wc -l < "$TMPDIR/$csv_file") - 1 ))  # subtract header
yaml_components=$(yq '[.. | select(has("name")) | .name] | length' "$f")
if [ "$csv_rows" -eq "$yaml_components" ]; then
    echo "  OK: $f -> $csv_file has $csv_rows data rows matching $yaml_components nodes"
else
    echo "  FAIL: $f -> $csv_file has $csv_rows data rows but expected $yaml_components nodes" >&2
    exit 1
fi

echo "Running pytest..."
"$VENV_DIR/bin/pytest" "$REPO_ROOT/tests/" -v

echo "All tests passed."
