#!/usr/bin/env python3
"""Normalize a Perplexity MCP ``answer`` before writing it to a file.

Why: Perplexity's WebUI returns answer text with bare URLs auto-linkified into
markdown ``[url](url)`` form, and models often wrap code/markup in a markdown
fence. Written verbatim, those artifacts corrupt HTML/CSS/JS (``href``, ``src``,
CSS ``url()``). Long answers are also truncated by the MCP result cap, so a
completeness check matters as much as the cleanup.

What it does:
  * accepts raw text, or a tool-result JSON blob via ``--json`` (reads
    ``answer`` at top level or under ``structuredContent.answer``)
  * strips one wrapping markdown code fence (```` ```html ... ``` ````)
  * rewrites ``[url](url)`` artifacts back to the bare URL; with
    ``--all-links`` it rewrites every ``[label](url)`` to its URL
  * verifies the result starts with ``--open`` and ends with ``--close``
  * reports byte size, line count, and any remaining ``](http`` artifacts

Usage:
  python3 normalize-answer.py raw.txt -o page.html
  python3 normalize-answer.py tool_result.json --json -o page.html
  cat raw.txt | python3 normalize-answer.py --open '<!DOCTYPE' --close '</html>'

Exit code 0 when verification passes, 1 otherwise. Output is still written on
failure so the caller can inspect it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

FENCE_RE = re.compile(r"^\s*`{3,}[a-zA-Z0-9_+-]*\s*\n(.*?)\n?`{3,}\s*$", re.DOTALL)
# [label](http(s)://...) -- the markdown link Perplexity injects.
LINK_RE = re.compile(r"\[([^\]\n]*)\]\((https?://[^)\s]+)\)")
ARTIFACT_RE = re.compile(r"\]\(https?://")


def extract_answer(raw: str) -> str:
    """Pull ``answer`` out of a tool-result JSON blob, else return raw text."""
    data = json.loads(raw)
    for candidate in (data, data.get("structuredContent") if isinstance(data, dict) else None,
                      data.get("result") if isinstance(data, dict) else None):
        if isinstance(candidate, dict) and isinstance(candidate.get("answer"), str):
            return candidate["answer"]
    raise SystemExit("--json: no 'answer' string found in the JSON input")


def strip_fences(text: str) -> str:
    m = FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def delinkify(text: str, all_links: bool) -> str:
    def repl(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        if all_links or label == href or label.startswith(("http://", "https://")):
            return label if label else href
        return href
    return LINK_RE.sub(repl, text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="input file (default: stdin)")
    ap.add_argument("-o", "--output", help="output file (default: stdout)")
    ap.add_argument("--json", action="store_true", help="parse input as a tool-result JSON blob and read 'answer'")
    ap.add_argument("--all-links", action="store_true", help="rewrite every [label](url) to its bare URL")
    ap.add_argument("--open", default="<!DOCTYPE", help="required start marker (default: '<!DOCTYPE')")
    ap.add_argument("--close", default="</html>", help="required end marker (default: '</html>')")
    ap.add_argument("--no-strip-fences", action="store_true", help="keep any wrapping code fence")
    args = ap.parse_args()

    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    if args.json:
        raw = extract_answer(raw)
    text = raw if args.no_strip_fences else strip_fences(raw)
    text = delinkify(text, args.all_links)
    text = text.strip() + "\n"

    cleaned_start = text.lstrip()
    cleaned_end = text.rstrip()
    artifacts = len(ARTIFACT_RE.findall(text))
    ok = cleaned_start.startswith(args.open) and cleaned_end.endswith(args.close) and artifacts == 0

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)

    summary = {
        "ok": ok,
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n"),
        "starts_with": args.open if cleaned_start.startswith(args.open) else cleaned_start[:20],
        "ends_with": args.close if cleaned_end.endswith(args.close) else cleaned_end[-20:],
        "remaining_link_artifacts": artifacts,
        "output": args.output or "<stdout>",
    }
    dest = sys.stdout if args.output else sys.stderr
    dest.write("normalize-answer: " + json.dumps(summary) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
