# Systems Engineering Diagrams

Tools for generating systems engineering diagrams from structured data definitions.

## Author

Aidan Nagorcka-Smith (aidanns@gmail.com)

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

Requires a `HOMEBREW_GITHUB_API_TOKEN` environment variable with a GitHub personal access token (repo scope) since this is a private repository.

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
systems-engineering function example/functional_decomposition.yaml -o output/

# Render all files in a directory
systems-engineering function example/ -o output/

# Render a subtree rooted at a specific function
systems-engineering function example/functional_decomposition.yaml -o output/ --root "Function A"

# Filter to functions matching a regex (case-insensitive, repeatable)
systems-engineering function example/functional_decomposition.yaml -o output/ --filter "function"

# Include all descendants of matched functions
systems-engineering function example/functional_decomposition.yaml -o output/ --filter "function" --include-descendants
```

This produces `.d2`, `.svg`, `.png`, `.md`, and `.csv` files in the output directory.

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

2. Verify that all leaf functions from a functional decomposition are allocated to configuration items:

```bash
systems-engineering product verify \
    -p example/product_breakdown.yaml \
    -f example/functional_decomposition.yaml
```

This checks that every leaf function has a corresponding allocation in the product breakdown and warns about any allocations that don't match a known function.

## Releasing

Releases are distributed via a private Homebrew tap (`aidanns/tools`).

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
