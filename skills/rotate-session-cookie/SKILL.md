---
name: rotate-session-cookie
description: Refresh the Perplexity session cookie when it expires or the gateway returns "session_expired". Use when pplx_session_status reports valid=false, a pplx_* tool returns error_type "session_expired", or the user says Perplexity stopped working.
---

# Rotate the Perplexity session cookie

The gateway authenticates to Perplexity with a session cookie stored in OpenClaw's
`mcpServers.perplexity.env.PERPLEXITY_SESSION_TOKEN`. That cookie expires (roughly yearly).

## When to use

- `pplx_session_status()` returns `valid: false` (or `expires` is in the past).
- Any `pplx_*` tool returns `error_type: "session_expired"`.
- The user reports Perplexity delegation failing with auth/403 errors.

## Steps

1. Confirm it is the cookie: run `pplx_session_status()` and read `valid` and `expires`.

2. Ask the user for a fresh cookie. Give them these exact steps:
   - Open https://www.perplexity.ai and sign in with the account that has Pro.
   - `F12` → **Application** → **Cookies** → `https://www.perplexity.ai`.
   - Copy the value of **`__Secure-pplx.session.<id>`** (Google sign-in) or
     **`__Secure-next-auth.session-token`** (email sign-in). The value is a long string starting with `eyJ`.
   - Alternatively, they can paste the `get-cookie.js` snippet from this repo into the console.

3. Update the token in `~/.openclaw/openclaw.json`
   (Windows: `C:\Users\<user>\.openclaw\openclaw.json`):
   - Locate `mcpServers.perplexity.env.PERPLEXITY_SESSION_TOKEN`.
   - Replace its value with the new cookie (no quotes around it in the value).

4. Reload OpenClaw's config (or restart the gateway) so the MCP server restarts with the new
   environment variable.

5. Verify: call `pplx_session_status()` and confirm `valid: true` and `account_tier: "pro"`.
   Then run a one-line query, e.g. `pplx_best(query="Say OK in one word")`.

## Notes

- The cookie value is the long `eyJ…` string; do not include surrounding quotes or the cookie name.
- There is no fallback credential: the WebUI cookie is the only authentication this gateway supports.
  If the user cannot produce a browser cookie, do not try other login methods without asking.
