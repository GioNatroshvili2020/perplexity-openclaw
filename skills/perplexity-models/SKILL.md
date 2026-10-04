---
name: perplexity-models
description: Route web research, summarization, file Q&A, code explanation/review, and deep reasoning to Perplexity Pro models via pplx_* MCP tools; file upload, file output, large-output handling, and recovery. NOT for the iterative write-run-fix coding loop.
whenToUse: When a task needs web search, current information, summarization, "find/explain X in a file", code explanation/review, or deep reasoning to conserve DeepSeek API tokens. Route iterative coding (write/run/debug/refactor) to the harness model (DeepSeek) instead.
---

# Perplexity Pro models (via MCP)

These tools run on the user's Perplexity Pro subscription (no DeepSeek API cost). Each call does web search + reasoning (or reads uploaded files) and returns an answer.

Tool names are prefixed per harness — use whatever your tool list shows (`perplexity__pplx_*`, `mcp__perplexity__pplx_*`, ...). Only models in `PERPLEXITY_MODELS` are exposed.

## Tools

| Tool | Use for |
|---|---|
| `pplx_best` | Fast default / unsure. |
| `pplx_gpt6_sol` | Broad research + technical synthesis. |
| `pplx_claude_s55` | Code explanation/review, file analysis, structured output. |
| `pplx_grok47` | Deep reasoning. |
| `pplx_kimi_k3_thinking` | Deep reasoning on hard topics. |
| `pplx_deep_research` | Maximum-depth research. |
| `pplx_session_status` | Cookie validity / tier / expiry. |

## Chat modes

- Default reuses a per-model conversation (same chat); pass `new_chat=true` for unrelated one-off tasks.
- Resume a specific past thread with `thread_uuid`.
- Threads are cached ~30 min of inactivity; after that a new one starts.

## Call pattern

1. Ask **one focused question per call**; put the full task context and the exact output format in `query` (the model sees only `query`).
2. Apply the chat-mode rule above.
3. Read the `answer` field — or `file` + `preview` when `output_path` is set; `search_results` holds citations (only with `include_search_results=true`).

## Files: upload, don't paste (token saver)

- `files=["/abs/a.py", "/abs/b.py"]` uploads local files as attachments; never paste file contents into `query`.
- When files are attached the tool switches to `search_focus="writing"` automatically so the model reads them instead of web-searching.
- Limits: 30 files, 50 MB each; requires the Pro account.

## Generating files: use `output_path`

- `output_path="/abs/out.py"` writes the cleaned answer to that file and returns `{file, bytes, preview}` instead of the full text — cheaper and no copy-paste.
- **The written file is NOT usually clean code.** It is the model's cleaned answer verbatim, which normally starts with a prose line (e.g. "Here's the self-contained file:") and wraps the actual code in a ``` fence. `strip_fence=true` only removes a single *wrapping* fence, so `prose + inner fence` stays dirty.
- For a clean artifact, say so in the query: "Output only the raw file contents — no prose, no explanation, no markdown fences." Then verify the file (e.g. `python3 -m py_compile`, or the head/tail check below).
- Post-clean mechanically with `scripts/normalize-answer.py` (below).

## Output controls

- `strip_fence=true` (default) — drop one wrapping markdown fence.
- `max_chars` — truncate the answer with an explicit `[truncated]` marker.
- `include_search_results=true` — also return citations (off by default to save tokens).
- `search_focus="web"` (default) or `"writing"` (pure generation; forced when files are attached).

## Large output (result cap)

- The tool result is size-capped: an `answer` longer than roughly 20k chars is silently truncated mid-stream with no error (observed 2026-10-03 on a full HTML page).
- Treat a missing sentinel or closing marker (e.g. no `</html>`) as truncation, not completion.
- Recover: ask for chunked delivery up front ("Part 1 of N, end exactly with `<SENTINEL>`, then wait for 'continue'") and keep it in the SAME thread; or read the full `answer` from the stored transcript JSON instead of trusting the truncated tool output.

## Sanitize before writing files

Perplexity auto-linkifies bare URLs in `answer` into markdown `[url](url)`; written verbatim this corrupts `href`/`src` and CSS `url()`.
Run `python3 ~/repos/perplexity-openclaw/scripts/normalize-answer.py <raw> -o <file>` (add `--json` for a raw tool-result blob) to strip the artifact, drop a wrapping fence, and verify the start/end markers in one step. It exits non-zero when truncation or leftover artifacts remain — gate the write on exit code 0.

## Verify and recover

- Before a long batch, call `pplx_session_status` and expect `{"valid": true, "account_tier": "pro"}`.
- `session_expired` -> `~/repos/perplexity-openclaw/skills/rotate-session-cookie/SKILL.md`, then ask the user for a fresh cookie.
- `model_access_denied` with `required_tier: "max"` -> switch to a Pro-tier model.
- Any other error -> `~/repos/perplexity-openclaw/skills/troubleshoot-perplexity-mcp/SKILL.md`; registry edits -> `update-model-registry`.

## Token economy & delegation boundaries

- Route **one-shot knowledge/retrieval/reasoning** here (research, summarization, "find X in a file", code explanation/review). Reserve DeepSeek (yourself) for orchestration and final synthesis.
- **Do NOT delegate the iterative coding loop** (write → run → debug → refactor → test). These models cannot read or execute their own code, so they fail to converge even when fed errors (verified: a trivial bug survived 6 iterations). Route that loop to the harness model (DeepSeek), which reads, runs, and patches files.
- One-shot code *generation* is OK when the spec is precise and you verify the output yourself (compile / head-tail check); *debugging* must go to the harness.
- Never paste file contents — upload via `files=[]`.
- Prefer `output_path` for generated code/HTML/docs and read the file; don't copy the answer back.
- Leave `include_search_results` off unless you actually need citations.
- `new_chat=true` for one-offs; reuse the same chat (default) for continuing tasks.

## Guardrails

- Never put secrets in `query`.
- Do not round-trip trivial chat through Perplexity; delegate only when it adds value.
