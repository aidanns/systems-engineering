#!/usr/bin/env bash

# Install Claude Code Notification/Stop hooks inside the devcontainer that bridge to the host.

set -euo pipefail

SETTINGS_DIR="${HOME}/.claude"
SETTINGS_FILE="${SETTINGS_DIR}/settings.json"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HOOK_CMD="${SCRIPT_DIR}/notify-host.sh"
STOP_HOOK_CMD="${HOOK_CMD} 'Response finished, ready for more input.'"

mkdir -p "${SETTINGS_DIR}"
if [ ! -f "${SETTINGS_FILE}" ]; then
  echo '{}' > "${SETTINGS_FILE}"
fi

if jq -e '(.hooks.Notification // empty), (.hooks.Stop // empty) | length > 0' "${SETTINGS_FILE}" >/dev/null 2>&1; then
  exit 0
fi

tmp=$(mktemp)
jq \
  --arg notify "${HOOK_CMD}" \
  --arg stop "${STOP_HOOK_CMD}" '
  .hooks //= {} |
  .hooks.Notification = [{ hooks: [{ type: "command", command: $notify }] }] |
  .hooks.Stop = [{ hooks: [{ type: "command", command: $stop }] }]
' "${SETTINGS_FILE}" > "${tmp}"
mv "${tmp}" "${SETTINGS_FILE}"
