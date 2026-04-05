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
- [yq](https://github.com/mikefarah/yq) installed and available on PATH (required for tests)

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

This produces `.d2`, `.svg`, `.png`, `.md`, and `.csv` files in the output directory.

## Releasing

Releases are distributed via a private Homebrew tap (`aidanns/tools`).

### Steps

1. **Update the version** in `pyproject.toml`.

2. **Commit the version bump**:
   ```bash
   git commit -am "chore: bump version to X.Y.Z"
   ```

3. **Create and push a git tag**:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

4. **Update the Homebrew formula** in `~/Projects/homebrew-tools/Formula/systems-engineering.rb`:
   - Change the `tag:` value to the new tag (e.g. `tag: "vX.Y.Z"`)
   - If Python dependencies changed, update the `resource` blocks (URLs and SHA256 hashes)

5. **Commit and push the formula update**:
   ```bash
   cd ~/Projects/homebrew-tools
   git commit -am "systems-engineering: update to vX.Y.Z"
   git push
   ```

6. **Test the update**:
   ```bash
   brew upgrade systems-engineering
   systems-engineering --help
   ```
