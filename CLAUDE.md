# Systems Engineering Diagrams

## Project Overview

CLI tools for generating systems engineering diagrams from YAML definitions, rendered via [d2](https://d2lang.com/).

## Structure

- `src/systems_engineering/cli.py` — Main CLI entry point. Reads YAML, outputs `.d2` definitions, renders to SVG/PNG via d2.
- `pyproject.toml` — Python package configuration. Defines the `systems-engineering` console entry point.
- `functional_decomposition/` — YAML files defining functional decomposition hierarchies.
- `output/` — Generated `.d2`, `.svg`, `.png`, and `.md` files (gitignored).
- `scripts/build.sh` — Creates virtualenv and installs the package in editable mode.
- `scripts/test.sh` — Validates YAML files, output file generation, and runs pytest semantic checks.
- `tests/test_cli.py` — Pytest suite with structural and golden file tests for all output types.
- `tests/golden/` — Golden files for expected output. Used for exact-match comparison in tests.
- `scripts/regenerate_golden.sh` — Regenerates golden files in `tests/golden/` from current CLI output.
- `scripts/generate.sh` — Generates all diagrams from `functional_decomposition/` to `output/`.

## YAML Schema for Functional Decomposition

```yaml
name: <root system name>
functions:
  - name: <function name>
    description: <string>     # optional
    recently_updated: <bool>  # optional, default false
    functions:                # optional nested children
      - name: <sub-function name>
        description: <string>
        recently_updated: <bool>
```

## Commands

```bash
# Set up virtualenv and install package
scripts/build.sh

# Run tests
scripts/test.sh

# Generate all diagrams
scripts/generate.sh

# Generate to a custom output directory
scripts/generate.sh /path/to/output

# Generate diagrams from a single file (direct)
.venv/bin/systems-engineering function functional_decomposition/example.yaml -o output/
```

## Dependencies

- Python 3.10+
- d2 (must be on PATH)
- pyyaml

## Conventions

- Use [conventional commits](https://www.conventionalcommits.org/) for all git commits (e.g. `feat:`, `fix:`, `docs:`, `chore:`).
- Before finishing work, confirm that `scripts/build.sh`, `scripts/test.sh`, and `scripts/generate.sh` all run successfully.
- When adding new output types or changing output format, regenerate and commit updated golden files in `tests/golden/` so changes are reviewable during PR review.
