#!/usr/bin/env bash

# Bridge Claude Code Notification/Stop hooks from the devcontainer to dev-notify-bridge on the host.

set -euo pipefail

INPUT=$(cat || true)
MESSAGE=$(printf '%s' "${INPUT}" | jq -r '.message // empty' 2>/dev/null || true)
if [ -n "${1:-}" ]; then
  MESSAGE=$1
fi
if [ -z "${MESSAGE}" ]; then
  MESSAGE="Claude Code event"
fi

TITLE="Claude Code"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  repo_name=$(basename "$(git rev-parse --show-toplevel)")
  if [ -n "${repo_name}" ]; then
    TITLE="Claude Code — ${repo_name}"
  fi
fi

payload=$(jq -nc --arg t "${TITLE}" --arg m "${MESSAGE}" '{title:$t, message:$m, sound:true}')

curl -fsS --max-time 2 \
  -X POST "http://host.docker.internal:6789/notify" \
  -H 'content-type: application/json' \
  -d "${payload}" >/dev/null 2>&1 || true
