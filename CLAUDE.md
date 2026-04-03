# Systems Engineering Diagrams

## Project Overview

CLI tools for generating systems engineering diagrams from YAML definitions, rendered via [d2](https://d2lang.com/).

## Structure

- `generate.py` — Main CLI entry point. Reads YAML, outputs `.d2` definitions, renders to SVG via d2.
- `functional_decomposition/` — YAML files defining functional decomposition hierarchies.
- `output/` — Generated `.d2` and `.svg` files (gitignored).
- `requirements.txt` — Python dependencies (pyyaml).
- `scripts/build.sh` — Creates virtualenv and installs dependencies.
- `scripts/test.sh` — Validates YAML files and d2 generation.
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
# Set up virtualenv and install dependencies
scripts/build.sh

# Run tests
scripts/test.sh

# Generate all diagrams
scripts/generate.sh

# Generate to a custom output directory
scripts/generate.sh /path/to/output

# Generate diagrams from a single file (direct)
.venv/bin/python generate.py functional_decomposition/example.yaml -o output/
```

## Dependencies

- Python 3.10+
- d2 (must be on PATH)
- pyyaml

## Conventions

- Use [conventional commits](https://www.conventionalcommits.org/) for all git commits (e.g. `feat:`, `fix:`, `docs:`, `chore:`).
- Before finishing work, confirm that `scripts/build.sh`, `scripts/test.sh`, and `scripts/generate.sh` all run successfully.
