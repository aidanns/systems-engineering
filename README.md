# Systems Engineering Diagrams

Tools for generating systems engineering diagrams from structured data definitions.

## Scope

This project provides CLI tools to generate systems engineering diagrams from YAML definitions. Diagrams are rendered using the [d2](https://d2lang.com/) framework.

### Supported Diagram Types

- **Functional Decomposition** — Define functional hierarchies in YAML and render them as SVG/PNG diagrams, markdown tables, and CSV exports.
- **Product Breakdown** — Define product breakdowns with configuration items and verify that all leaf functions are allocated.

## Installation

### Via Homebrew (recommended)

```bash
brew tap aidanns/tools
brew install systems-engineering
```

### Via direct installer (Linux)

Prerequisites: Python 3.10+ and [d2](https://d2lang.com/) must be installed.

Download and inspect the installer, then run it:

```bash
curl -fsSL https://raw.githubusercontent.com/aidanns/systems-engineering/main/install.sh -o install.sh
bash install.sh
```

To install a specific version:

```bash
bash install.sh v1.2.3
```

To uninstall:

```bash
bash install.sh --uninstall
# Or manually: rm -rf ~/.local/share/systems-engineering ~/.local/bin/systems-engineering
```

### From source

- Python 3.10+
- [d2](https://d2lang.com/) installed and available on PATH
- [yq](https://github.com/mikefarah/yq) installed and available on PATH (required for tests)

```bash
scripts/build.sh
```

### Dev Container

A dev container configuration is provided in `.devcontainer/` with Python 3, d2, and Claude Code pre-installed. Use it via VS Code ("Reopen in Container"), JetBrains Gateway, or the CLI:

```bash
# One-time setup: install devcontainer CLI, build and start the container
scripts/setup.sh

# Open a shell inside the dev container
npx devcontainer exec --workspace-folder . bash
```

#### Host notifications

Claude Code's notification and stop hooks rely on host-only tools (`terminal-notifier`, iTerm, etc.) and don't fire from inside the container. To bridge them, the devcontainer's `initializeCommand` starts [`dev-notify-bridge`](https://www.npmjs.com/package/dev-notify-bridge) on the host (via `npx`, requires `node`/`npx` on the host PATH — already a prerequisite for the devcontainer CLI). The container's Notification and Stop hooks are wired by `postCreateCommand` to POST to `http://host.docker.internal:6789/notify`, producing native macOS notifications titled `Claude Code — <repo>`. Logs are at `.devcontainer/dev-notify-bridge-logs/dev-notify-bridge.log`.

## Library Usage

The data model is importable as a Python library, so other tools can read and manipulate the same YAML files:

```python
from pathlib import Path
from systems_engineering import (
    Function,
    Component,
    ConfigurationItem,
    load_yaml,
    parse_functional_decomposition,
    parse_product_breakdown,
    find_subtree,
    filter_tree,
    collect_leaf_function_names,
    collect_allocated_functions,
)

# Load and parse a functional decomposition
fd = parse_functional_decomposition(load_yaml(Path("path/to/functional_decomposition.yaml")))
print(fd.name)  # root function name
for child in fd.functions:
    print(f"  {child.name}: {child.description}")

# Load and parse a product breakdown
pb = parse_product_breakdown(load_yaml(Path("path/to/product_breakdown.yaml")))
for component in pb.components:
    for ci in component.configuration_items:
        print(f"  {ci.name}: {ci.functions}")

# Tree operations
subtree = find_subtree(fd, "Power Management")
filtered = filter_tree(fd, ["Power"], include_descendants=True)
leaf_names = collect_leaf_function_names(fd)
allocated = collect_allocated_functions(pb)
```

## Usage

Check the installed version:

```bash
systems-engineering --version
```

### Functional Decomposition

1. Create a YAML definition file (see `example/` for reference):

```yaml
name: System Name
functions:
  - name: Function A
    description: Description of Function A.
    functions:
      - name: Sub-function A1
        description: Description of Sub-function A1.
      - name: Sub-function A2
        description: Description of Sub-function A2.
  - name: Function B
    description: Description of Function B.
```

2. Generate diagrams:

```bash
# Render a single file
systems-engineering function diagram example/functional_decomposition.yaml -o output/

# Render all files in a directory
systems-engineering function diagram example/ -o output/

# Render a subtree rooted at a specific function
systems-engineering function diagram example/functional_decomposition.yaml -o output/ --root "Function A"

# Filter to functions matching a regex (case-insensitive, repeatable)
systems-engineering function diagram example/functional_decomposition.yaml -o output/ --filter "function"

# Include all descendants of matched functions
systems-engineering function diagram example/functional_decomposition.yaml -o output/ --filter "function" --include-descendants

# Highlight updated functions with a red border (case-insensitive regex, repeatable)
systems-engineering function diagram example/functional_decomposition.yaml -o output/ --highlight-updated "Thermal|Store"

# Highlight new functions with a blue border (case-insensitive regex, repeatable)
systems-engineering function diagram example/functional_decomposition.yaml -o output/ --highlight-new "Data"
```

This produces `.d2`, `.svg`, `.png`, `.md`, and `.csv` files in the output directory.

3. Verify that all leaf functions are covered by test annotations:

```bash
# Verify test coverage of all leaf functions
systems-engineering function verify example/functional_decomposition.yaml -t tests/

# Using directory mode (finds functional_decomposition.yaml inside)
systems-engineering function verify example/ -t tests/
```

Test files should annotate which functions they cover using `@pytest.mark.covers_function`:

```python
import pytest

@pytest.mark.covers_function("Generate Power", "Store Power")
def test_power_functions():
    ...
```

The command uses static analysis (AST parsing) to find annotations — it does not execute the tests. It reports which leaf functions are covered, which are missing, and exits non-zero if any are uncovered.

### Product Breakdown

1. Create a product breakdown YAML file (see `example/` for reference):

```yaml
name: System Name
components:
  - name: Subsystem A
    description: Description of Subsystem A.
    components:
      - name: Sub-subsystem A1
        description: Description of Sub-subsystem A1.
        configuration_items:
          - name: Hardware Unit 1
            description: Description of Hardware Unit 1.
            functions:
              - Function A1
              - Function A2
```

2. Generate product breakdown diagrams:

```bash
# Generate from a file
systems-engineering product diagram example/product_breakdown.yaml -o output/

# Generate from a directory (expects product_breakdown.yaml inside)
systems-engineering product diagram example/ -o output/

# Render a subtree rooted at a specific component or CI
systems-engineering product diagram example/product_breakdown.yaml -o output/ --root "Power Subsystem"

# Filter to nodes matching a regex (case-insensitive, repeatable)
systems-engineering product diagram example/product_breakdown.yaml -o output/ --filter "power"

# Include all descendants of matched nodes
systems-engineering product diagram example/product_breakdown.yaml -o output/ --filter "power" --include-descendants
```

This produces `.d2`, `.svg`, `.png`, `.md`, and `.csv` files in the output directory.

3. Verify that all leaf functions from a functional decomposition are allocated to configuration items:

```bash
systems-engineering product verify \
    -p example/product_breakdown.yaml \
    -f example/functional_decomposition.yaml
```

This checks that every leaf function has a corresponding allocation in the product breakdown and warns about any allocations that don't match a known function.

## Releasing

Releases are distributed via a Homebrew tap (`aidanns/tools`) and as wheel artifacts attached to GitHub releases (used by the direct installer).

### Using the release script

`scripts/release.sh` automates steps 1–4 below. It determines the version bump from conventional commit messages since the last tag:

- **Breaking changes** (`feat!:`, `fix!:`, etc.) → major version bump
- **Features** (`feat:`) → minor version bump
- **All other changes** (`fix:`, `docs:`, `chore:`, etc.) → patch version bump

```bash
scripts/release.sh
```

The script runs tests, updates `pyproject.toml`, commits, tags, and pushes. After it completes, follow step 5 onwards to update the Homebrew formula.

### Manual steps

1. **Update the version** in `pyproject.toml`.

2. **Run tests** to confirm the release is clean:
   ```bash
   scripts/build.sh && scripts/test.sh && scripts/generate.sh
   ```

3. **Commit the version bump**:
   ```bash
   git commit -am "chore: bump version to X.Y.Z"
   ```

4. **Create and push a git tag**:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

5. **Update the Homebrew formula** at [github.com/aidanns/homebrew-tools](https://github.com/aidanns/homebrew-tools) (`Formula/systems-engineering.rb`):
   - Change the `tag:` value to the new tag (e.g. `tag: "vX.Y.Z"`)
   - If Python dependencies changed, update the `resource` blocks (URLs and SHA256 hashes)
   - If fixing the formula without a new tag, increment the `revision` field instead

6. **Commit and push the formula update**.

7. **Test the update**:
   ```bash
   brew upgrade systems-engineering
   systems-engineering --help
   ```

## License

MIT. See [LICENSE](LICENSE) for details.

## Author

Aidan Nagorcka-Smith (aidanns@gmail.com)
