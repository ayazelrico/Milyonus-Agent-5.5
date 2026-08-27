"""Deep web research from the terminal (wired as `milyonus research`)."""

from __future__ import annotations

from rich.console import Console

from milyonus.brand import GLYPH, PALETTE

console = Console()


def run_research(query: str, *, sources: int = 6, subqueries: int = 3) -> int:
    """Plan, search, read multiple sources, and synthesize a cited report."""
    import asyncio

    from milyonus.config.env import load_env
    from milyonus.config.loader import load_config
    from milyonus.providers.router import build_provider
    from milyonus.research.deep import deep_research
    from milyonus.research.search import active_provider

    load_env()
    cfg = load_config()
    provider = build_provider(cfg.provider)
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Deep research[/] "
        f"[dim]search: {active_provider()} · reading up to {sources} sources…[/]\n"
    )
    report = asyncio.run(
        deep_research(query, provider=provider, max_subqueries=subqueries, max_sources=sources)
    )
    console.print(report.render())
    return 0
