# Perplexity → OpenClaw MCP gateway

Give an [OpenClaw](https://openclaw.ai) agent (running DeepSeek or any local model) the ability to
**delegate tasks to your Perplexity Pro models** — GPT-5.6 Terra, Claude Sonnet 5, Gemini 3.8 Flash,
Grok 4.6, and more — with web search, using only your Perplexity **session cookie** (no official API key).

It wraps [`perplexity-webui-scraper`](https://github.com/henrique-coder/perplexity-webui-scraper)
into an MCP server that drives Perplexity's internal WebUI API. The scraper source is vendored here
(MIT) with patches that add: **same-chat-by-default**, a `new_chat` toggle, thread continuation, and
**cookie-expiry detection**.

## What you get

- One MCP tool per Perplexity model — `pplx_best`, `pplx_claude_s50`, `pplx_gpt56_terra`, etc.
- A `pplx_session_status` health tool (valid / account tier / expiry timestamp).
- **Same chat by default** — repeated calls continue one conversation; `new_chat=true` starts fresh.
- Automatic **cookie-expiry** reporting when the session token stops working.
- [Skills](skills/) that teach the agent how to reconfigure the source on its own.

---

## For the OpenClaw agent (setup)

You are setting this up on the machine that runs OpenClaw. Do these steps in order. If a step
fails, consult the `troubleshoot-perplexity-mcp` skill.

### 1. Prerequisites

- OpenClaw is installed; its config is at `~/.openclaw/openclaw.json`
  (Windows: `C:\Users\<user>\.openclaw\openclaw.json`).
- The machine can reach `github.com`, `pypi.org`, and `www.perplexity.ai`.

### 2. Install the MCP server

- **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File setup.ps1
  ```
- **macOS / Linux:**
  ```bash
  bash setup.sh
  ```

This installs `uv` if needed and builds the MCP server + dependencies into
`perplexity-webui-scraper/.venv`, then prints the exact config block to paste.

### 3. Add the server to OpenClaw

Paste the printed block into `~/.openclaw/openclaw.json`, replacing `YOUR_COOKIE`:

```json5
{
  "mcpServers": {
    "perplexity": {
      "command": "<printed path to .venv/.../perplexity-webui-scraper>",
      "args": ["mcp"],
      "env": { "PERPLEXITY_SESSION_TOKEN": "YOUR_COOKIE" }
    }
  }
}
```

### 4. Get the session cookie

See [Getting your session cookie](#getting-your-session-cookie). Put the value in
`PERPLEXITY_SESSION_TOKEN`.

### 5. Reload and verify

1. Reload OpenClaw's config (or restart the gateway).
2. Run `pplx_session_status()` — expect `valid: true` and `account_tier: "pro"`.
3. Run a one-line test: `pplx_best(query="Reply OK in one word", new_chat=true)`.

---

## Getting your session cookie

The cookie is the long `eyJ…` string Perplexity uses to authenticate your logged-in session.

### Option A — browser console snippet

Open `https://www.perplexity.ai`, press `F12` → **Console**, paste the contents of
[`get-cookie.js`](get-cookie.js), and press Enter. It prints the cookie and copies the value.

> **Heads-up:** Perplexity's session cookie is **HttpOnly**, so JavaScript often cannot read it.
> If the snippet reports "not readable", use Option B.

### Option B — copy from DevTools (always works)

1. Sign in to [perplexity.ai](https://www.perplexity.ai) with the account that has **Pro**.
2. `F12` → **Application** (Chrome/Edge) or **Storage** (Firefox) → **Cookies** →
   `https://www.perplexity.ai`.
3. Copy the **value** of **`__Secure-pplx.session.<id>`** (Google sign-in) or
   **`__Secure-next-auth.session-token`** (email sign-in).

> Google vs email sign-in changes the cookie *name*; the token **value** works either way.
> Use whichever account holds your Pro subscription. Treat the value like a password and never
> commit it (the repo's `.gitignore` excludes `.env` files).

---

## Chat modes & file handling

Each model tool accepts these optional controls:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `new_chat` | `false` | Reuse this model's ongoing conversation (same chat). Set `true` to start fresh. |
| `thread_uuid` | *(none)* | Continue a *specific* thread by its UUID (advanced). |
| `files` | *(none)* | Local file paths to **upload** as attachments (no pasting contents). |
| `output_path` | *(none)* | Write the cleaned answer to this file; returns `{file, bytes, preview}` instead of the full text. |
| `strip_fence` | `true` | Drop a single wrapping markdown code fence. |
| `max_chars` | *(none)* | Truncate the answer with an explicit marker. |
| `include_search_results` | `false` | Also return web citations (off by default to save tokens). |

```text
# Continuous agentic task — reuse the same chat (default):
pplx_claude_s50(query="Research Georgian restaurants in Prague")
pplx_claude_s50(query="Narrow it to ones near Žižkov")     # remembers the previous answer

# Single-use task — start fresh:
pplx_claude_s50(query="Summarize this", new_chat=true)

# Upload files instead of pasting code (token saver):
pplx_claude_s50(query="Fix the bug in these files", files=["/abs/src/app.py", "/abs/tests/test_app.py"])

# Generate code straight to a downloadable file:
pplx_claude_s50(query="Write a FastAPI CRUD app", output_path="/abs/out/app.py")
```

### File upload & download (token saver)

- **Upload:** pass local paths via `files` — the tool uploads them as attachments and auto-switches to
  `writing` mode so the model reads the files instead of web-searching. Max 30 files / 50 MB each.
- **Download:** pass `output_path` — the cleaned answer (link artifacts reverted, code fence stripped)
  is written to that path, and the tool returns a short `{file, bytes, preview}`.

"Same chat" is **per model** — each model keeps its own thread. Conversations are cached for
30 minutes of inactivity, then a new one starts automatically.

---

## Cookie expiry notification

1. **Proactive check** — `pplx_session_status` returns validity, tier, and expiry:
   ```json
   { "valid": true, "account_tier": "pro", "email": "you@gmail.com",
     "expires": "2026-11-02T18:37:12Z" }
   ```
2. **Automatic on failure** — when the cookie is expired/invalid, every model tool returns:
   ```json
   { "error": "Your Perplexity session cookie has expired or is invalid. Sign in again at
     perplexity.ai, copy the '__Secure-pplx.session.<id>' cookie value, update
     PERPLEXITY_SESSION_TOKEN in OpenClaw, and reshare the new cookie.",
     "error_type": "session_expired" }
   ```

When either happens, follow the `rotate-session-cookie` skill, then tell the user to reshare a
fresh cookie.

---

## Models available on Pro

`perplexity/best`, `perplexity/deep-research`, `openai/gpt-5.6-terra` (+`-thinking`),
`anthropic/claude-sonnet-5` (+`-thinking`), `google/gemini-3.8-flash` (+`-thinking`),
`x-ai/grok-4.6` (+`-thinking`), `moonshot/kimi-k3-thinking`, `z-ai/glm-5.3`,
`nvidia/nemotron-3-ultra-thinking`, and more. Models tagged `max` (e.g. `openai/gpt-5.6-sol`,
`anthropic/claude-opus-5`) return a tier error on Pro.

---

## Skills (for the agent)

This repo ships skills that let the agent reconfigure the gateway without the user knowing
internals. Copy them into the agent's skills directory, or just tell the agent to read them from
`skills/`:

| Skill | Purpose |
|---|---|
| [`skills/rotate-session-cookie/SKILL.md`](skills/rotate-session-cookie/SKILL.md) | Refresh an expired cookie. |
| [`skills/update-model-registry/SKILL.md`](skills/update-model-registry/SKILL.md) | Add / remove / edit models in `models.json`. |
| [`skills/troubleshoot-perplexity-mcp/SKILL.md`](skills/troubleshoot-perplexity-mcp/SKILL.md) | Map errors to fixes. |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools don't appear in OpenClaw | Check `command` path matches setup output; reload config; read OpenClaw MCP logs. |
| `PERPLEXITY_SESSION_TOKEN not set` | Add `env.PERPLEXITY_SESSION_TOKEN` inside the `perplexity` entry. |
| `session_expired` | Rotate the cookie (see skill). |
| `model_access_denied` / 403 | Model needs a higher tier (Pro vs Max). |
| `rate_limited` (429) | Wait and retry; reduce call frequency. |

---

## Files

```
perplexity-openclaw/
├── README.md                     # this file
├── setup.ps1 / setup.sh          # one-command installer
├── openclaw-mcp.json5            # reference OpenClaw config
├── get-cookie.js                 # browser snippet to print/copy the session cookie
├── skills/                       # AI skills for self-service reconfiguration
│   ├── rotate-session-cookie/SKILL.md
│   ├── update-model-registry/SKILL.md
│   └── troubleshoot-perplexity-mcp/SKILL.md
└── perplexity-webui-scraper/     # vendored MCP server source (with patches)
```

## Attribution

The vendored `perplexity-webui-scraper` is by Henrique Moreira ([repo](https://github.com/henrique-coder/perplexity-webui-scraper)),
MIT license — see `perplexity-webui-scraper/LICENSE`. The wrapper, patches, skills, and setup
scripts in this repository are provided as-is with no warranty. Use of Perplexity's internal API is
unofficial and subject to Perplexity's Terms of Service.
