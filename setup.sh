#!/usr/bin/env bash
# One-command setup for the Perplexity -> OpenClaw MCP server (macOS / Linux).
#   bash setup.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$HERE/perplexity-webui-scraper"

# 1. Ensure uv is installed.
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (package manager)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || {
    echo "uv was installed but is not on PATH. Close and reopen the terminal, then re-run this script." >&2
    exit 1
  }
fi

# 2. Install the MCP server + dependencies into a local .venv.
echo "Installing Perplexity MCP server + dependencies (first run downloads ~a minute)..."
(cd "$PROJ" && uv sync --extra mcp --no-dev)

BIN="$PROJ/.venv/bin/perplexity-webui-scraper"

echo ""
echo "=== Setup complete ==="
echo "Add the block below to  ~/.openclaw/openclaw.json  (replace YOUR_COOKIE):"
echo ""
cat <<EOF
  "mcpServers": {
    "perplexity": {
      "command": "$BIN",
      "args": ["mcp"],
      "env": { "PERPLEXITY_SESSION_TOKEN": "YOUR_COOKIE" }
    }
  }
EOF
echo ""
