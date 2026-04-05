#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMS_ENGINEERING="$REPO_ROOT/.venv/bin/systems-engineering"

if [ ! -f "$SYSTEMS_ENGINEERING" ]; then
    echo "Error: systems-engineering CLI not found in virtualenv. Run scripts/build.sh first." >&2
    exit 1
fi

PYTHON="$REPO_ROOT/.venv/bin/python"

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
    "$SYSTEMS_ENGINEERING" function "$f" -o "$TMPDIR" 2>/dev/null || true
    stem="$(basename "${f%.*}")"
    for ext in d2 svg png md csv; do
        output_file="${stem}_functions.$ext"
        if [ -f "$TMPDIR/$output_file" ]; then
            echo "  OK: $f -> $output_file"
        else
            echo "  FAIL: $f (no $output_file output)" >&2
            exit 1
        fi
    done
    # Check that CSV row count matches the number of functions in the YAML.
    csv_file="${stem}_functions.csv"
    csv_rows=$(( $(wc -l < "$TMPDIR/$csv_file") - 1 ))  # subtract header
    yaml_functions=$(yq '[.functions // [] | .. | select(has("name")) | .name] | length' "$f")
    if [ "$csv_rows" -eq "$yaml_functions" ]; then
        echo "  OK: $f -> $csv_file has $csv_rows data rows matching $yaml_functions functions"
    else
        echo "  FAIL: $f -> $csv_file has $csv_rows data rows but YAML has $yaml_functions functions" >&2
        exit 1
    fi
done

echo "All tests passed."
