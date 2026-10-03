#!/usr/bin/env bash
# The repo is the single source of truth for these skills.
# Install / refresh them into an OpenClaw agent workspace; re-run after every `git pull`.
#
#   ./install-skills.sh [agent-id]      # default: coordinator
#
# Each ./skills/<name>/ is installed with `openclaw skills install ... --force`,
# which copies it into <agent-workspace>/skills/<name>. Edit skills ONLY here,
# then re-run this script so the agent picks up the change.
set -euo pipefail

AGENT="${1:-coordinator}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v openclaw >/dev/null 2>&1 || { echo "openclaw CLI not found on PATH" >&2; exit 1; }

shopt -s nullglob
for d in "$HERE"/skills/*/; do
  [ -f "$d/SKILL.md" ] || continue
  echo "==> $(basename "$d")"
  openclaw skills install "$d" --agent "$AGENT" --force
done

echo
echo "Installed from $(basename "$HERE")/skills into agent '$AGENT'."
echo "Verify: openclaw skills list --agent $AGENT"
