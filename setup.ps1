# One-command setup for the Perplexity -> OpenClaw MCP server (Windows).
#   Run with PowerShell:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Join-Path $here "perplexity-webui-scraper"

# 1. Ensure uv is installed (it manages Python + dependencies).
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv (package manager)..."
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $uvDir = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path (Join-Path $uvDir "uv.exe")) { $env:Path = "$uvDir;$env:Path" }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv was installed but is not on PATH. Close and reopen the terminal, then re-run this script."
    }
}

# 2. Install the MCP server + dependencies into a local .venv.
Write-Host "Installing Perplexity MCP server + dependencies (first run downloads ~a minute)..."
Push-Location $proj
try {
    uv sync --extra mcp --no-dev
} finally {
    Pop-Location
}

# 3. Print the ready-to-paste OpenClaw config.
$bin = Join-Path $proj ".venv\Scripts\perplexity-webui-scraper.exe"
$binFwd = ($bin -replace '\\', '/')

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host "Add the block below to  ~/.openclaw/openclaw.json  (replace YOUR_COOKIE):" -ForegroundColor Cyan
Write-Host ""
Write-Host "  `"mcpServers`": {"
Write-Host "    `"perplexity`": {"
Write-Host "      `"command`": `"$binFwd`","
Write-Host "      `"args`": [`"mcp`"],"
Write-Host "      `"env`": { `"PERPLEXITY_SESSION_TOKEN`": `"YOUR_COOKIE`" }"
Write-Host "    }"
Write-Host "  }"
Write-Host ""
