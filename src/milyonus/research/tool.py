"""Research tools for the agent: web_search and deep_research."""

from __future__ import annotations

from typing import Any

from milyonus.providers.base import Provider
from milyonus.research.deep import deep_research
from milyonus.research.search import search_web
from milyonus.tools.registry import Tool


def make_research_tools(provider: Provider) -> list[Tool]:
    async def web_search(args: dict[str, Any]) -> str:
        results = await search_web(args["query"], k=int(args.get("k", 6)))
        if not results:
            return "no results"
        return "\n".join(
            f"[{i}] {r.title} — {r.url}\n    {r.snippet[:160]}" for i, r in enumerate(results, 1)
        )

    async def deep_research_tool(args: dict[str, Any]) -> str:
        report = await deep_research(
            args["query"],
            provider=provider,
            max_subqueries=int(args.get("subqueries", 3)),
            max_sources=int(args.get("sources", 6)),
        )
        return report.render()

    return [
        Tool(
            name="web_search",
            description="Search the web and return titles, URLs, and snippets.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
                "required": ["query"],
            },
            handler=web_search,
            risk="caution",
        ),
        Tool(
            name="deep_research",
            description=(
                "Run multi-source web research on a question: plans sub-queries, "
                "reads several sources, and returns a cited synthesis with a "
                "numbered source list."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "subqueries": {"type": "integer"},
                    "sources": {"type": "integer"},
                },
                "required": ["query"],
            },
            handler=deep_research_tool,
            risk="caution",
        ),
    ]
