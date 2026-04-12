#!/usr/bin/env bash

# Install or upgrade systems-engineering from a GitHub release.

set -euo pipefail

GITHUB_REPO="aidanns/systems-engineering"
INSTALL_DIR="$HOME/.local/share/systems-engineering"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
BIN_LINK="$BIN_DIR/systems-engineering"

# --- Argument parsing ---

LOCAL_DIR=""
VERSION=""
UNINSTALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --local)
            LOCAL_DIR="$2"
            shift 2
            ;;
        *)
            VERSION="$1"
            shift
            ;;
    esac
done

# --- Uninstall ---

if $UNINSTALL; then
    echo "Uninstalling systems-engineering..."
    rm -f "$BIN_LINK"
    rm -rf "$VENV_DIR"
    rmdir "$INSTALL_DIR" 2>/dev/null || true
    echo "Removed: $BIN_LINK"
    echo "Removed: $VENV_DIR"
    exit 0
fi

# --- Helper functions ---

gh_curl() {
    curl -fsSL -H "Authorization: token $GITHUB_TOKEN" \
         -H "Accept: application/vnd.github+json" "$@"
}

gh_download() {
    curl -fsSL -H "Authorization: token $GITHUB_TOKEN" \
         -H "Accept: application/octet-stream" -o "$2" "$1"
}

# --- Prerequisite checks ---

# Check Python 3.10+
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "Error: Python 3.10+ is required but not found." >&2
    echo "" >&2
    echo "Install Python 3.10+ for your platform:" >&2
    echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv" >&2
    echo "  RHEL/Fedora:    sudo dnf install python3" >&2
    echo "  NixOS:          nix-env -iA nixpkgs.python3" >&2
    exit 1
fi

# Check d2
if ! command -v d2 >/dev/null 2>&1; then
    echo "Error: d2 is required but not found on PATH." >&2
    echo "" >&2
    echo "Install d2 for your platform:" >&2
    echo "  Ubuntu/Debian:  curl -fsSL https://d2lang.com/install.sh | sh -s --" >&2
    echo "  RHEL/Fedora:    curl -fsSL https://d2lang.com/install.sh | sh -s --" >&2
    echo "  NixOS:          nix-env -iA nixpkgs.d2" >&2
    echo "  General:        https://d2lang.com/" >&2
    exit 1
fi

# --- Acquire wheel and checksum ---

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

if [[ -n "$LOCAL_DIR" ]]; then
    # Local mode: copy wheel and checksum from a local directory (used by integration tests).
    wheel_path="$(ls "$LOCAL_DIR"/*.whl 2>/dev/null | head -1)"
    if [[ -z "$wheel_path" ]]; then
        echo "Error: no .whl file found in $LOCAL_DIR" >&2
        exit 1
    fi
    wheel_name="$(basename "$wheel_path")"
    checksum_path="$(ls "$LOCAL_DIR"/*.sha256 2>/dev/null | head -1)"
    if [[ -z "$checksum_path" ]]; then
        echo "Error: no .sha256 file found in $LOCAL_DIR" >&2
        exit 1
    fi
    cp "$wheel_path" "$TMPDIR/"
    cp "$checksum_path" "$TMPDIR/"
else
    # Remote mode: fetch from GitHub releases.
    : "${GITHUB_TOKEN:?GITHUB_TOKEN must be set (private repo)}"

    # Resolve version
    if [[ -z "$VERSION" ]]; then
        VERSION=$("$PYTHON" -c "
import json, sys
data = json.load(sys.stdin)
print(data['tag_name'])
" < <(gh_curl "https://api.github.com/repos/$GITHUB_REPO/releases/latest"))
    fi

    # Normalize: ensure leading v
    VERSION="v${VERSION#v}"
    echo "Installing systems-engineering $VERSION..."

    # Fetch release metadata and extract asset URLs
    release_json=$(gh_curl "https://api.github.com/repos/$GITHUB_REPO/releases/tags/$VERSION")

    asset_info=$("$PYTHON" -c "
import json, sys
data = json.load(sys.stdin)
assets = {a['name']: a['url'] for a in data.get('assets', [])}
whl = [(n, u) for n, u in assets.items() if n.endswith('.whl')]
chk = [(n, u) for n, u in assets.items() if n.endswith('.sha256')]
if not whl:
    print('ERROR: no .whl asset found in release', file=sys.stderr)
    sys.exit(1)
if not chk:
    print('ERROR: no .sha256 asset found in release', file=sys.stderr)
    sys.exit(1)
# name url name url
print(whl[0][0])
print(whl[0][1])
print(chk[0][0])
print(chk[0][1])
" <<< "$release_json")

    wheel_name=$(echo "$asset_info" | sed -n '1p')
    wheel_url=$(echo "$asset_info" | sed -n '2p')
    checksum_name=$(echo "$asset_info" | sed -n '3p')
    checksum_url=$(echo "$asset_info" | sed -n '4p')

    echo "Downloading $wheel_name..."
    gh_download "$wheel_url" "$TMPDIR/$wheel_name"
    gh_download "$checksum_url" "$TMPDIR/$checksum_name"
fi

# --- Verify checksum ---

echo "Verifying checksum..."
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$TMPDIR" && sha256sum -c *.sha256)
else
    (cd "$TMPDIR" && shasum -a 256 -c *.sha256)
fi

# --- Install into venv ---

wheel_file="$(ls "$TMPDIR"/*.whl | head -1)"

echo "Installing into $VENV_DIR..."
mkdir -p "$INSTALL_DIR"
"$PYTHON" -m venv --clear "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --no-cache-dir "$wheel_file"

# --- Create symlink ---

mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/systems-engineering" "$BIN_LINK"

# --- Verify ---

if "$BIN_LINK" --version >/dev/null 2>&1; then
    echo ""
    echo "systems-engineering installed successfully."
    echo "  Binary: $BIN_LINK"
    echo "  Venv:   $VENV_DIR"
else
    echo "Error: installation verification failed." >&2
    exit 1
fi

# --- PATH warning ---

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "Warning: $BIN_DIR is not in your PATH."
        echo "Add it to your shell profile:"
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        ;;
esac

echo ""
echo "To uninstall, run:"
echo "  rm -rf $INSTALL_DIR $BIN_LINK"
