---
name: update-model-registry
description: Add, remove, or edit Perplexity models in the gateway's model registry. Use when a model is missing from the tool list, a model returns model_access_denied with a seemingly wrong tier, or Perplexity has added/renamed/removed models.
---

# Update the Perplexity model registry

Each Perplexity model is exposed as one MCP tool. The catalog lives in:

`perplexity-webui-scraper/src/perplexity_webui_scraper/_static/models.json`

## When to use

- A model the user wants is missing from the MCP tool list.
- A tool returns `model_access_denied` but the account tier looks correct.
- Perplexity changed its models (check https://www.perplexity.ai/rest/models/config/v2 for the
  current internal identifiers and official list).

## Model entry fields

| Field | Meaning |
|---|---|
| `id` | Canonical id, e.g. `openai/gpt-5.6-terra`. |
| `identifier` | Perplexity's internal model identifier (from the v2 config endpoint). |
| `tool_name` | snake_case MCP tool name, e.g. `pplx_gpt56_terra`. Must be unique. |
| `min_tier` | `free`, `pro`, `max`, or `null`. |
| `mode` | `copilot`, `search`, or `research`. |
| `status` | `available`, `unknown`, or `unavailable`. |
| `is_official` | `true` if listed in Perplexity's WebUI, else `false`. |

## Steps

1. Edit `perplexity-webui-scraper/src/perplexity_webui_scraper/_static/models.json`:
   - Keep `perplexity/best` and `perplexity/deep-research` first.
   - Keep every `id` and `tool_name` unique.
   - Prefer official identifiers from the v2 config endpoint; do not invent identifiers.

2. Rebuild the local environment so the change is picked up (idempotent):
   - Windows: `powershell -ExecutionPolicy Bypass -File setup.ps1`
   - macOS/Linux: `bash setup.sh`

3. Restart/reload OpenClaw so it re-lists the tools.

4. Verify: list the tools and confirm the new model appears; run it once with a short query and a
   `new_chat=true` flag to avoid polluting an ongoing conversation.

## Notes

- Only change `status` to `unavailable` when you have evidence (a real failure), not on suspicion.
- A model with a non-`available` status requires the agent to pass `allow_risky_model=true`.
