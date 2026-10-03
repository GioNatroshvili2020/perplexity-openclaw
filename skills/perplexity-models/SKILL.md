---
name: perplexity-models
description: Use the Perplexity MCP tools (mcp__perplexity__*) for web research, code analysis, and technical reasoning through Perplexity Pro models (GPT-5.6 Terra, Kimi K3 Thinking, Claude Sonnet 5), offloading work from DeepSeek API tokens. Load before calling any mcp__perplexity__ tool.
whenToUse: When a task needs web search, current information, code/file analysis, or deep technical reasoning that should be routed to a Perplexity Pro model to conserve DeepSeek API usage.
---

# Perplexity Pro models (via MCP)

These tools run on the user's Perplexity Pro subscription (no DeepSeek API cost). Each call does web search + reasoning (or reads uploaded files) and returns an answer.

## Tools (all prefixed `mcp__perplexity__`)

| Tool | Use for |
|---|---|
| `pplx_best` | Fast default for general lookups. |
| `pplx_gpt56_terra` | Broad research + technical synthesis. |
| `pplx_kimi_k3_thinking` | Deep reasoning on hard technical topics. |
| `pplx_claude_s50` | Coding, file analysis, structured output. |
| `pplx_session_status` | Check cookie validity / tier / expiry. |

## How to use

- Ask **one focused question per call**. Don't bundle unrelated questions.
- Default reuses a per-model conversation (same chat); pass `new_chat=true` for unrelated one-off tasks.
- `search_focus="web"` for current info; `"writing"` for pure generation.

## Files: upload instead of pasting (token saver)

For coding tasks, **never paste file contents into the query**. Pass local file paths via `files`:

- `files=["/abs/path/src.py", "/abs/path/tests.py"]` uploads them as attachments.
- When files are attached, the tool auto-switches to `writing` mode so the model reads the files rather than web-searching.
- Max 30 files, 50 MB each. Requires the Pro account (which this is).

## Generating files: write, don't paste back

For code/markup generation, ask the model to produce a file and write it straight to disk via `output_path`:

- `output_path="/abs/path/out.py"` writes the cleaned answer to that file and returns `{file, bytes, preview}` instead of the full text — saves tokens and makes the result downloadable.
- The answer is cleaned automatically: `[url](url)` artifacts reverted, one wrapping code fence stripped (disable with `strip_fence=false`).

## Output controls

- `strip_fence=true` (default) — drop a single wrapping ``` code fence.
- `max_chars` — truncate the answer with an explicit `[truncated]` marker.
- `include_search_results=true` — also return web citations (off by default to save tokens).

## Token economy

Route heavy research/reasoning to these tools; reserve DeepSeek (yourself) for orchestration and final synthesis. Avoid your own web_search/web_fetch when a Perplexity tool covers the need. Only the models listed in `PERPLEXITY_MODELS` are exposed — if a model is missing, ask the user to add it to that env var.

## Tier note

Models tagged "max" (e.g. gpt-5.6-sol, claude-opus-5) are NOT on Pro and return `model_access_denied`. Use Pro-tier models instead.
