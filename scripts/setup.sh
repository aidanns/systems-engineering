#!/usr/bin/env bash

# One-time setup: install devcontainer CLI, build the container, and install
# the Python package inside it.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing devcontainer CLI..."
npm install --prefix "$REPO_ROOT"

echo "Building devcontainer..."
npx devcontainer build --workspace-folder "$REPO_ROOT"

echo "Starting devcontainer and running build..."
npx devcontainer up --workspace-folder "$REPO_ROOT"

echo "Setup complete."
echo "Run commands inside the container with: npx devcontainer exec --workspace-folder . <command>"
