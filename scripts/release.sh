#!/usr/bin/env bash

# Create a release: auto-determine version bump, run tests, commit, tag, and push.

set -euo pipefail

source "$(dirname "$0")/env.sh"

# Validate arguments
case "${1:-}" in
    --yes|"") ;;
    *) echo "Usage: $0 [--yes]"; exit 1 ;;
esac

# Guard: must be on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "Error: releases must be created from the main branch (currently on '$current_branch')."
    exit 1
fi

# Guard: working tree must be clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: working tree is not clean. Commit or stash changes first."
    exit 1
fi

# Determine the latest release tag
latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -z "$latest_tag" ]; then
    echo "No existing tags found. Defaulting to v0.0.0."
    latest_tag="v0.0.0"
fi

echo "Latest release: $latest_tag"

# Parse current version
version="${latest_tag#v}"
IFS='.' read -r major minor patch <<< "$version"

# Determine version bump from conventional commit prefixes since last tag
commits=$(git log "${latest_tag}..HEAD" --oneline 2>/dev/null || git log --oneline)

if [ -z "$commits" ]; then
    echo "No commits since $latest_tag. Nothing to release."
    exit 0
fi

echo ""
echo "Commits since $latest_tag:"
echo "$commits"
echo ""

# Check for breaking changes (major) or features (minor)
bump="patch"
if echo "$commits" | grep -qiE '^\w+ \w+(\([^)]+\))?!:'; then
    bump="major"
elif echo "$commits" | grep -qiE '^\w+ feat(\([^)]+\))?:'; then
    bump="minor"
fi

case "$bump" in
    major) major=$((major + 1)); minor=0; patch=0 ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    patch) patch=$((patch + 1)) ;;
esac

new_version="${major}.${minor}.${patch}"
new_tag="v${new_version}"

echo "Version bump: $bump ($latest_tag -> $new_tag)"
echo ""

# Guard: tag must not already exist
if git rev-parse "$new_tag" >/dev/null 2>&1; then
    echo "Error: tag $new_tag already exists."
    exit 1
fi

# Confirm with user (skip with --yes flag)
if [[ "${1:-}" != "--yes" ]]; then
    read -r -p "Proceed with release $new_tag? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Run tests
echo ""
echo "Running tests..."
"$REPO_ROOT/scripts/build.sh"
"$REPO_ROOT/scripts/test.sh"
"$REPO_ROOT/scripts/generate.sh"

# Update version in pyproject.toml
echo ""
echo "Updating version in pyproject.toml..."
if [[ "$OSTYPE" == darwin* ]]; then
    sed -i '' "s/^version = \".*\"/version = \"${new_version}\"/" "$REPO_ROOT/pyproject.toml"
else
    sed -i "s/^version = \".*\"/version = \"${new_version}\"/" "$REPO_ROOT/pyproject.toml"
fi

# Commit and tag
git add "$REPO_ROOT/pyproject.toml"
git commit -m "chore: bump version to ${new_version}"
git tag "$new_tag"

echo ""
echo "Pushing to origin..."
git push origin main --tags

echo ""
echo "Building wheel..."
BUILD_TMPDIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_TMPDIR"' EXIT

"$VENV_DIR/bin/pip" install --quiet build
"$VENV_DIR/bin/python" -m build --wheel --outdir "$BUILD_TMPDIR" "$REPO_ROOT"

wheel_path="$(ls "$BUILD_TMPDIR"/*.whl)"
wheel_filename="$(basename "$wheel_path")"
checksum_path="$BUILD_TMPDIR/${wheel_filename}.sha256"

if command -v sha256sum >/dev/null 2>&1; then
    (cd "$BUILD_TMPDIR" && sha256sum "$wheel_filename" > "$checksum_path")
else
    (cd "$BUILD_TMPDIR" && shasum -a 256 "$wheel_filename" > "$checksum_path")
fi

echo "  Wheel: $wheel_filename"
echo "  Checksum: $(cat "$checksum_path")"

echo ""
echo "Creating GitHub Release..."
if command -v gh >/dev/null 2>&1; then
    gh release create "$new_tag" \
        --title "$new_tag" \
        --generate-notes \
        --notes-start-tag "$latest_tag" \
        --latest \
        "$wheel_path" \
        "$checksum_path"
else
    echo "Warning: gh CLI not found; skipping GitHub Release creation."
    echo "Create it manually at https://github.com/aidanns/systems-engineering/releases/new?tag=$new_tag"
fi

echo ""
echo "Release $new_tag complete."
echo ""
echo "Next steps:"
echo "  1. Update the Homebrew formula at github.com/aidanns/homebrew-tools"
echo "     - Change tag: \"$latest_tag\" to tag: \"$new_tag\""
echo "  2. Test with: brew upgrade systems-engineering"
echo "  3. Linux users can upgrade via the installer:"
echo "     curl -fsSL -H \"Authorization: token \$GITHUB_TOKEN\" \\"
echo "         https://raw.githubusercontent.com/aidanns/systems-engineering/main/install.sh | bash"
