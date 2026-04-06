#!/usr/bin/env bash
# Shared helper to resolve the platform-specific virtualenv directory.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-$(uname -s)-$(uname -m)"
