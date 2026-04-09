# Systems Engineering Diagrams

## Project Overview

CLI tools for generating systems engineering diagrams from YAML definitions, rendered via [d2](https://d2lang.com/).

## Structure

- `src/systems_engineering/cli.py` — Main CLI entry point. Reads YAML, outputs `.d2` definitions, renders to SVG/PNG via d2.
- `pyproject.toml` — Python package configuration. Defines the `systems-engineering` console entry point.
- `example/` — Example YAML files (functional decomposition and product breakdown).
- `output/` — Generated `.d2`, `.svg`, `.png`, `.md`, and `.csv` files (gitignored).
- `scripts/build.sh` — Creates virtualenv and installs the package in editable mode.
- `scripts/test.sh` — Validates YAML files, output file generation, and runs pytest semantic checks.
- `tests/test_cli.py` — Pytest suite with structural and golden file tests for all output types.
- `tests/golden/` — Golden files for expected output. Used for exact-match comparison in tests.
- `scripts/regenerate_golden.sh` — Regenerates golden files in `tests/golden/` from current CLI output.
- `scripts/generate.sh` — Generates all diagrams from `example/` to `output/`.
- `scripts/build-wheel.sh` — Builds a wheel and SHA256 checksum file into a given output directory. Used by `release.sh` and `test-install.sh`.
- `scripts/release.sh` — Creates a release: auto-determines version bump, runs tests, builds a wheel + SHA256 checksum, commits, tags, pushes, and attaches wheel artifacts to the GitHub release.
- `scripts/test-install.sh` — Docker-based integration tests for `install.sh`. Requires Docker.
- `install.sh` — Installer script for Linux. Downloads a wheel from GitHub releases and installs into `~/.local/share/systems-engineering/venv` with a symlink at `~/.local/bin/systems-engineering`. Supports `--local <dir>` for testing with local artifacts.
- `tests/install/` — Dockerfiles for installer integration tests (base Ubuntu, no-d2, old-python variants).
- `design/` — CLI's own functional decomposition and product breakdown (dogfooding). Contains `functional_decomposition.yaml` and `product_breakdown.yaml` sources and generated artefacts (SVG, CSV, etc.) checked into the repo. Keep updated per Conventions.

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
.venv-$(uname -s)-$(uname -m)/bin/systems-engineering function diagram example/functional_decomposition.yaml -o output/

# Generate diagrams from all files in a directory
.venv-$(uname -s)-$(uname -m)/bin/systems-engineering function diagram example/ -o output/

# Generate product breakdown diagrams from a single file
.venv-$(uname -s)-$(uname -m)/bin/systems-engineering product diagram product_breakdown/example.yaml -o output/

# Verify all leaf functions are allocated to configuration items
.venv-$(uname -s)-$(uname -m)/bin/systems-engineering product verify \
    -p example/product_breakdown.yaml \
    -f example/functional_decomposition.yaml

# Verify using directory mode (finds matching files automatically)
.venv-$(uname -s)-$(uname -m)/bin/systems-engineering product verify -p example/ -f example/
```

## Dev Container

A dev container configuration is provided in `.devcontainer/`. It uses `mcr.microsoft.com/devcontainers/base:ubuntu` with Python 3, d2, and Claude Code pre-installed.

```bash
# One-time setup: install devcontainer CLI, build and start the container
scripts/setup.sh

# Run a command inside the dev container
npx devcontainer exec --workspace-folder . bash
```

The dev container can also be opened directly from VS Code ("Reopen in Container") or JetBrains Gateway.

## Dependencies

- Python 3.10+
- d2 (must be on PATH)
- pyyaml
- Node.js (for devcontainer CLI, dev dependency)

## Conventions

- Use [conventional commits](https://www.conventionalcommits.org/) for all git commits (e.g. `feat:`, `fix:`, `docs:`, `chore:`).
- All bash scripts in `scripts/` must be portable across macOS and Linux.
- Before finishing work, confirm that `scripts/build.sh`, `scripts/test.sh`, and `scripts/generate.sh` all run successfully.
- When adding new output types or changing output format, regenerate and commit updated golden files in `tests/golden/` so changes are reviewable during PR review.
- Keep `design/functional_decomposition.yaml` up to date as new functionality is added to the CLI. Regenerate with: `.venv-$(uname -s)-$(uname -m)/bin/systems-engineering function diagram design/functional_decomposition.yaml -o design/`
- Keep `design/product_breakdown.yaml` up to date when components or dependencies change. Regenerate with: `.venv-$(uname -s)-$(uname -m)/bin/systems-engineering product diagram design/product_breakdown.yaml -o design/`
- Before finishing implementation work, check that `README.md` is consistent with the current functionality. Update it if new features, flags, or commands have been added.

## Development Workflow

- Before commencing development, pull the latest changes from GitHub so work begins from the tip of `main`.
- All changes — including small ones like renames, doc tweaks, or regenerating design artefacts — must be developed in a git worktree and landed via a pull request. Do not commit directly to `main`, even for trivial work.
- New features must be developed in a git worktree:
  - Use the built-in `EnterWorktree` tool (while on `main`) rather than running `git worktree add` manually. It creates the worktree under `.claude/worktrees/` and switches the session into it.
  - Use `ExitWorktree` when finished. Pass `action: "keep"` to preserve the work or `action: "remove"` for a clean teardown (use `discard_changes: true` to force-remove a worktree with uncommitted changes).
  - For isolated parallel work, prefer `Agent(..., isolation: "worktree")` to spawn a subagent in its own throwaway worktree.
- The worktree must use a branch named `feature/[feature-name]` (kebab-case) based on the tip of `main`.
- The worktree directory must be named `[feature-name]` (matching the branch suffix), located at `.claude/worktrees/[feature-name]`. For example, branch `feature/configure-dotfiles` lives in `.claude/worktrees/configure-dotfiles`.
- After changes are made, commit them to the feature branch, push the branch to GitHub, and open a pull request from the feature branch into `main`.

## Releasing

- Run `scripts/release.sh` to create a release. Pass `--yes` to skip the confirmation prompt. It auto-determines the version bump from conventional commit messages (breaking → major, feat → minor, other → patch).
- The release script builds a wheel and SHA256 checksum file and attaches both to the GitHub release. The `curl | bash` installer downloads from these release assets.
- Version is defined in `pyproject.toml`. Tags follow `vX.Y.Z` format.
- The Homebrew formula is at `github.com/aidanns/homebrew-tools/Formula/systems-engineering.rb` and must be updated with the new tag after each release.
- If Python dependencies change, the formula's `resource` blocks (URLs and SHA256 hashes) must also be updated.
- See README.md for the full step-by-step release process.
