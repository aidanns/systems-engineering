#!/usr/bin/env bash

# Shared environment variables sourced by other scripts.
# Sets REPO_ROOT and VENV_DIR.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-$(uname -s)-$(uname -m)"
