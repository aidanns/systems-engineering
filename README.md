# Systems Engineering Diagrams

Tools for generating systems engineering diagrams from structured data definitions.

## Author

Aidan Nagorcka-Smith (aidanns@gmail.com)

## Scope

This project provides CLI tools to generate systems engineering diagrams from YAML definitions. Diagrams are rendered using the [d2](https://d2lang.com/) framework.

### Supported Diagram Types

- **Functional Decomposition** — Define functional hierarchies in YAML and render them as SVG diagrams.

## Installation

### Via Homebrew (recommended)

```bash
brew tap aidanns/tools
brew install systems-engineering
```

Requires a `HOMEBREW_GITHUB_API_TOKEN` environment variable with a GitHub personal access token (repo scope) since this is a private repository.

### From source

- Python 3.10+
- [d2](https://d2lang.com/) installed and available on PATH

```bash
scripts/build.sh
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
systems-engineering function functional_decomposition/example.yaml -o output/

# Render all files in a directory
systems-engineering function functional_decomposition/ -o output/
```

This produces `.d2`, `.svg`, `.png`, and `.md` files in the output directory.
