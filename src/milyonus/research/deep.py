"""Deep web research — plan, search, read multiple sources, synthesize, cite.

The engine turns a question into a cited report:
  1. Plan   — the model breaks the question into focused sub-queries.
  2. Search — each sub-query is searched; unique URLs are collected.
  3. Read   — top sources are fetched (SSRF-guarded, deduped, truncated).
  4. Synthesize — the model writes a thorough answer that cites [n] each source.

Search and fetch are injectable so the whole pipeline is testable offline. Bounds
(sub-queries, sources, per-source length) keep cost and context in check —
addressing the "context grows, cost grows" concern directly.
"""

from __future__ import annotations

import json
import re as _re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from milyonus.providers.base import CompletionRequest, Message, Provider
from milyonus.research.search import SearchResult, search_web
from milyonus.security.redact import redact
from milyonus.security.ssrf import SSRFBlocked, check_url

_SCRIPT_STYLE = _re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", _re.S | _re.I)
_TAGS = _re.compile(r"<[^>]+>")
_WS = _re.compile(r"[ \t]*\n\s*\n\s*", _re.S)


def _html_to_text(html: str) -> str:
    """Strip scripts/styles/tags to readable text for synthesis."""
    from html import unescape

    text = _SCRIPT_STYLE.sub(" ", html)
    text = _TAGS.sub(" ", text)
    text = unescape(text)
    text = _re.sub(r"[ \t]+", " ", text)
    text = _WS.sub("\n\n", text)
    return text.strip()


SearchFn = Callable[[str, int], Awaitable[list[SearchResult]]]
FetchFn = Callable[[str], Awaitable[str]]


@dataclass(slots=True)
class ResearchReport:
    query: str
    answer: str
    sources: list[SearchResult] = field(default_factory=list)

    def render(self) -> str:
        lines = [self.answer, "", "Sources:"]
        for i, s in enumerate(self.sources, 1):
            lines.append(f"  [{i}] {s.title} — {s.url}")
        return "\n".join(lines)


async def _default_fetch(url: str) -> str:
    import httpx

    try:
        check_url(url)
    except SSRFBlocked as exc:
        return f"(blocked: {exc})"
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as c:
            resp = await c.get(url, headers={"User-Agent": "MilyonusResearch/5.5"})
            ctype = resp.headers.get("content-type", "")
            body = _html_to_text(resp.text) if "html" in ctype else resp.text
            return redact(body)
    except httpx.HTTPError as exc:
        return f"(fetch error: {exc})"


async def _collect_text(provider: Provider, system: str, prompt: str, max_tokens: int) -> str:
    req = CompletionRequest(
        system=system,
        messages=[Message(role="user", content=prompt)],
        max_output_tokens=max_tokens,
        temperature=0.0,
    )
    text = ""
    async for ev in provider.stream(req):
        if ev.kind == "text":
            text += ev.delta
    return text.strip()


async def _plan(provider: Provider, query: str, n: int) -> list[str]:
    out = await _collect_text(
        provider,
        "You plan web research. Break the question into focused search queries.",
        f"Question: {query}\nReturn a JSON array of {n} short, distinct search "
        f"queries that together answer it. JSON only.",
        256,
    )
    start, end = out.find("["), out.rfind("]")
    if start != -1 and end != -1:
        try:
            qs = json.loads(out[start : end + 1])
            return [str(q) for q in qs][:n] or [query]
        except (ValueError, TypeError):
            pass
    return [query]


_SYNTH_SYSTEM = """You are a rigorous research analyst. Write a thorough, \
well-structured answer using ONLY the provided sources. Cite every claim with \
[n] matching the source number. If the sources disagree or are insufficient, say \
so. Do not invent facts or citations."""


async def deep_research(
    query: str,
    *,
    provider: Provider,
    search_fn: SearchFn | None = None,
    fetch_fn: FetchFn | None = None,
    max_subqueries: int = 3,
    max_sources: int = 6,
    per_source_chars: int = 4000,
) -> ResearchReport:
    async def _search(q: str, k: int) -> list[SearchResult]:
        return await search_web(q, k=k)

    search_fn = search_fn or _search
    fetch_fn = fetch_fn or _default_fetch

    # 1. plan
    subqueries = await _plan(provider, query, max_subqueries)

    # 2. search + dedup
    results: list[SearchResult] = []
    seen: set[str] = set()
    for sq in subqueries:
        for r in await search_fn(sq, 5):
            if r.url and r.url not in seen:
                seen.add(r.url)
                results.append(r)
    results = results[:max_sources]

    if not results:
        return ResearchReport(query, "No sources found for this query.", [])

    # 3. read
    blocks = []
    for i, r in enumerate(results, 1):
        text = (await fetch_fn(r.url))[:per_source_chars]
        blocks.append(f"[{i}] {r.title} ({r.url})\n{text}")

    # 4. synthesize
    prompt = (
        f"Research question: {query}\n\nSources:\n\n"
        + "\n\n---\n\n".join(blocks)
        + "\n\nWrite the cited answer now."
    )
    answer = await _collect_text(provider, _SYNTH_SYSTEM, prompt, 2048)
    return ResearchReport(query, answer, results)
