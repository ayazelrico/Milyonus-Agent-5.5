"""Web search — keyless by default, pluggable when a key is present.

Providers, in priority order:
  1. Tavily   if TAVILY_API_KEY  (LLM-oriented search API)
  2. Brave    if BRAVE_API_KEY   (Brave Search API)
  3. DuckDuckGo HTML (no key) — scrapes html.duckduckgo.com; the default so
     research works out of the box.

The HTML parser is pure and unit-tested. Result URLs are returned as-is; the
caller (deep research) validates each with the SSRF guard before fetching.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

import httpx

_DDG_URL = "https://html.duckduckgo.com/html/"
_UA = "Mozilla/5.0 (compatible; MilyonusResearch/5.5)"


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


# --- DuckDuckGo HTML parsing (pure) ------------------------------------

_A_RE = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_SNIP_RE = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip(html: str) -> str:
    return unescape(_TAG_RE.sub("", html)).strip()


def _real_url(href: str) -> str:
    """DDG wraps results as //duckduckgo.com/l/?uddg=<encoded>; unwrap it."""
    if "uddg=" in href:
        q = parse_qs(urlparse("https:" + href if href.startswith("//") else href).query)
        if "uddg" in q:
            return unquote(q["uddg"][0])
    return href


def parse_ddg_html(html: str, k: int = 8) -> list[SearchResult]:
    titles = _A_RE.findall(html)
    snippets = _SNIP_RE.findall(html)
    out: list[SearchResult] = []
    for i, (href, title_html) in enumerate(titles[:k]):
        url = _real_url(href)
        if not url.startswith("http"):
            continue
        snippet = _strip(snippets[i]) if i < len(snippets) else ""
        out.append(SearchResult(title=_strip(title_html), url=url, snippet=snippet))
    return out


# --- providers ----------------------------------------------------------


async def _search_tavily(query: str, k: int, client: httpx.AsyncClient) -> list[SearchResult]:
    resp = await client.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": k,
            "search_depth": "advanced",
        },
    )
    data = resp.json()
    return [
        SearchResult(title=r.get("title", ""), url=r.get("url", ""), snippet=r.get("content", ""))
        for r in data.get("results", [])
    ]


async def _search_brave(query: str, k: int, client: httpx.AsyncClient) -> list[SearchResult]:
    resp = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": k},
        headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"]},
    )
    data = resp.json()
    return [
        SearchResult(
            title=r.get("title", ""), url=r.get("url", ""), snippet=r.get("description", "")
        )
        for r in data.get("web", {}).get("results", [])
    ]


async def _search_ddg(query: str, k: int, client: httpx.AsyncClient) -> list[SearchResult]:
    resp = await client.post(_DDG_URL, data={"q": query}, headers={"User-Agent": _UA})
    return parse_ddg_html(resp.text, k)


def active_provider() -> str:
    if os.environ.get("TAVILY_API_KEY"):
        return "tavily"
    if os.environ.get("BRAVE_API_KEY"):
        return "brave"
    return "duckduckgo"


async def search_web(
    query: str, *, k: int = 8, client: httpx.AsyncClient | None = None
) -> list[SearchResult]:
    """Search the web with the best available provider (keyless by default)."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=20.0, follow_redirects=True)
    try:
        provider = active_provider()
        if provider == "tavily":
            return await _search_tavily(query, k, client)
        if provider == "brave":
            return await _search_brave(query, k, client)
        return await _search_ddg(query, k, client)
    finally:
        if own:
            await client.aclose()
