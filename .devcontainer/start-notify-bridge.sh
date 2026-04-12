#!/usr/bin/env bash

# Start dev-notify-bridge on the host so the devcontainer can deliver notifications.

set -euo pipefail

PORT=6789
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOG_DIR="${SCRIPT_DIR}/dev-notify-bridge-logs"
LOG_FILE="${LOG_DIR}/dev-notify-bridge.log"

if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  exit 0
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "start-notify-bridge: npx not found on host PATH; skipping" >&2
  exit 0
fi

mkdir -p "${LOG_DIR}"

nohup npx --yes github:aidanns/dev-notify-bridge --port "${PORT}" \
  >>"${LOG_FILE}" 2>&1 &
disown || true
