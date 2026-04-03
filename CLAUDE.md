# Systems Engineering Diagrams

## Project Overview

CLI tools for generating systems engineering diagrams from YAML definitions, rendered via [d2](https://d2lang.com/).

## Structure

- `generate.py` — Main CLI entry point. Reads YAML, outputs `.d2` definitions, renders to SVG via d2.
- `functional_decomposition/` — YAML files defining functional decomposition hierarchies.
- `output/` — Generated `.d2` and `.svg` files (gitignored).
- `requirements.txt` — Python dependencies (pyyaml).

## YAML Schema for Functional Decomposition

```yaml
name: <root system name>
functions:
  - name: <function name>
    functions:          # optional nested children
      - name: <sub-function name>
```

## Commands

```bash
# Set up virtualenv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Generate diagrams from a single file
.venv/bin/python generate.py functional_decomposition/example.yaml -o output/

# Generate diagrams from all files in a directory
.venv/bin/python generate.py functional_decomposition/ -o output/
```

## Dependencies

- Python 3.10+
- d2 (must be on PATH)
- pyyaml

## Conventions

- Use [conventional commits](https://www.conventionalcommits.org/) for all git commits (e.g. `feat:`, `fix:`, `docs:`, `chore:`).
