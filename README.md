# Systems Engineering Diagrams

Tools for generating systems engineering diagrams from structured data definitions.

## Author

Aidan Nagorcka-Smith (aidanns@gmail.com)

## Scope

This project provides CLI tools to generate systems engineering diagrams from YAML definitions. Diagrams are rendered using the [d2](https://d2lang.com/) framework.

### Supported Diagram Types

- **Functional Decomposition** — Define functional hierarchies in YAML and render them as SVG diagrams.

## Prerequisites

- Python 3.10+
- [d2](https://d2lang.com/) installed and available on PATH
- Python dependencies:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```

## Usage

### Functional Decomposition

1. Create a YAML definition file in `functional_decomposition/`:

```yaml
name: System Name
functions:
  - name: Function A
    description: Description of Function A.
    recently_updated: false
    functions:
      - name: Sub-function A1
        description: Description of Sub-function A1.
        recently_updated: true
      - name: Sub-function A2
        description: Description of Sub-function A2.
        recently_updated: false
  - name: Function B
    description: Description of Function B.
    recently_updated: false
```

2. Generate diagrams:

```bash
# Render a single file
.venv/bin/python generate.py functional_decomposition/example.yaml -o output/

# Render all files in a directory
.venv/bin/python generate.py functional_decomposition/ -o output/
```

This produces `.d2` and `.svg` files in the output directory.
