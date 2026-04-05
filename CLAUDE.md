# Systems Engineering Diagrams

## Project Overview

CLI tools for generating systems engineering diagrams from YAML definitions, rendered via [d2](https://d2lang.com/).

## Structure

- `src/systems_engineering/cli.py` — Main CLI entry point. Reads YAML, outputs `.d2` definitions, renders to SVG/PNG via d2.
- `pyproject.toml` — Python package configuration. Defines the `systems-engineering` console entry point.
- `functional_decomposition/` — YAML files defining functional decomposition hierarchies.
- `product_breakdown/` — YAML files defining product breakdown hierarchies with CI-to-function allocations.
- `output/` — Generated `.d2`, `.svg`, `.png`, `.md`, and `.csv` files (gitignored).
- `scripts/build.sh` — Creates virtualenv and installs the package in editable mode.
- `scripts/test.sh` — Validates YAML files, output file generation, and runs pytest semantic checks.
- `tests/test_cli.py` — Pytest suite with structural and golden file tests for all output types.
- `tests/golden/` — Golden files for expected output. Used for exact-match comparison in tests.
- `scripts/regenerate_golden.sh` — Regenerates golden files in `tests/golden/` from current CLI output.
- `scripts/generate.sh` — Generates all diagrams from `functional_decomposition/` to `output/`.
- `scripts/release.sh` — Creates a release: auto-determines version bump, runs tests, commits, tags, and pushes.
- `design/` — CLI's own functional decomposition (dogfooding). Contains `functions.yaml` source and generated artefacts (SVG, CSV, etc.) checked into the repo. Keep updated per Conventions.

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

## YAML Schema for Product Breakdown

```yaml
name: <root product/system name>
components:
  - name: <component name>
    description: <string>              # optional
    components:                        # optional nested children
      - name: <sub-component name>
        description: <string>
    configuration_items:               # typically on leaf components
      - name: <CI name>
        description: <string>          # optional
        functions:                     # allocated function names (strings)
          - <function name>
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

# Verify all leaf functions are allocated to configuration items
.venv/bin/systems-engineering product verify \
    -p product_breakdown/example.yaml \
    -f functional_decomposition/example.yaml
```

## Dependencies

- Python 3.10+
- d2 (must be on PATH)
- pyyaml

## Conventions

- Use [conventional commits](https://www.conventionalcommits.org/) for all git commits (e.g. `feat:`, `fix:`, `docs:`, `chore:`).
- All bash scripts in `scripts/` must be portable across macOS and Linux.
- Before finishing work, confirm that `scripts/build.sh`, `scripts/test.sh`, and `scripts/generate.sh` all run successfully.
- When adding new output types or changing output format, regenerate and commit updated golden files in `tests/golden/` so changes are reviewable during PR review.
- Keep `design/functions.yaml` up to date as new functionality is added to the CLI. Regenerate with: `.venv/bin/systems-engineering function design/functions.yaml -o design/`
- Before finishing implementation work, check that `README.md` is consistent with the current functionality. Update it if new features, flags, or commands have been added.

## Releasing

- Run `scripts/release.sh` to create a release. Pass `--yes` to skip the confirmation prompt. It auto-determines the version bump from conventional commit messages (breaking → major, feat → minor, other → patch).
- Version is defined in `pyproject.toml`. Tags follow `vX.Y.Z` format.
- The Homebrew formula is at `github.com/aidanns/homebrew-tools/Formula/systems-engineering.rb` and must be updated with the new tag after each release.
- If Python dependencies change, the formula's `resource` blocks (URLs and SHA256 hashes) must also be updated.
- See README.md for the full step-by-step release process.
