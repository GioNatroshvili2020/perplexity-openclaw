---
name: troubleshoot-perplexity-mcp
description: Diagnose and fix common Perplexity MCP gateway failures. Use when a pplx_* tool returns an error, the tools don't appear in OpenClaw, or the user reports the Perplexity integration is broken.
---

# Troubleshoot the Perplexity MCP gateway

## Error → fix

| Symptom | Likely cause | Fix |
|---|---|---|
| `error_type: "session_expired"` | Cookie expired or invalid | Rotate it — see the `rotate-session-cookie` skill. |
| `error_type: "model_access_denied"` | Model requires a higher tier | Use a `pro`-tier model, or tell the user it needs Max. |
| `error_type: "rate_limited"` (429) | Perplexity throttled the account | Wait 30–60s, retry, and reduce call frequency. |
| `error_type: "thread_not_found"` | `thread_uuid` older than 30 min idle | Omit `thread_uuid` or set `new_chat=true`. |
| Tools don't appear in OpenClaw | Command/path wrong or config not reloaded | Check `mcpServers.perplexity.command` matches setup output; check OpenClaw's MCP logs; reload config. |
| `PERPLEXITY_SESSION_TOKEN not set` | `env` block missing or misplaced | Add `env.PERPLEXITY_SESSION_TOKEN` inside the `perplexity` entry of `mcpServers`. |
| `custom_model_invalid` | Bad `custom:` identifier | Pass a valid internal identifier and `allow_risky_model=true`. |

## Steps

1. Isolate the problem: run `pplx_session_status()` first. A bad cookie shows up there before any
   model-specific error.

2. Match the error to the table and apply the fix.

3. If you edited any file under `perplexity-webui-scraper/src/`, rebuild and reload:
   - Re-run `setup.ps1` / `setup.sh`.
   - Reload/restart OpenClaw.

4. Verify with a minimal call: `pplx_best(query="Reply OK", new_chat=true)`.

## Escalation

- If a fix is not in the table, gather the exact error dict, the `pplx_session_status()` output, and
  the last lines of OpenClaw's MCP log for this server, then report those to the user — do not
  guess at Perplexity's internal endpoints.
