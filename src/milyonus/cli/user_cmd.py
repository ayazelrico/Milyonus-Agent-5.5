"""`milyonus user ...` — inspect and query the cross-session user model.

The user model is the verified-memory store scoped to one user (by provenance
actor). These commands show what has been learned about a user across sessions,
ask natural-language questions of that model, and add an observation (which is
proposed through the pipeline, never written directly)."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE
from milyonus.memory.store import MemoryStore

user_app = typer.Typer(help="Cross-session user model.")
console = Console()

_DEFAULT_USER = "local"


def _model(user_ref: str, *, with_pipeline: bool = False):
    from milyonus.config.loader import load_config
    from milyonus.memory.semantic import SemanticMemory
    from milyonus.memory.usermodel import UserModel

    cfg = load_config()
    store = MemoryStore()
    try:
        sem = SemanticMemory(store, config=cfg.memory)
    except Exception:
        sem = None
    pipeline = None
    if with_pipeline:
        from milyonus.memory.pipeline import MemoryPipeline

        pipeline = MemoryPipeline(store, config=cfg.memory, semantic=sem)
    return UserModel(store, user_ref=user_ref, config=cfg.memory, semantic=sem, pipeline=pipeline)


@user_app.command("show")
def user_show(user: str = typer.Option(_DEFAULT_USER, "--user", help="User ref")) -> None:
    """Show the durable, trust-ranked model of a user."""
    model = _model(user)
    stats = model.stats()
    console.print(f"[bold {PALETTE['cyan_400']}]{GLYPH} User model — {user}[/]")
    if not stats["total"]:
        console.print("[dim]  nothing learned yet.[/]")
        raise typer.Exit()
    tiers = ", ".join(f"{k}={v}" for k, v in stats.items() if k != "total")
    console.print(f"  {stats['total']} facts  ({tiers})\n")
    console.print(model.profile(budget=4000) or "[dim]  (all below trust floor)[/]")


@user_app.command("ask")
def user_ask(
    query: str,
    user: str = typer.Option(_DEFAULT_USER, "--user", help="User ref"),
) -> None:
    """Dialectic query: 'what do we know about the user re: X'."""
    model = _model(user)
    hits = model.ask(query)
    if not hits:
        console.print("[dim]nothing known about the user for that[/]")
        raise typer.Exit()
    for m, score in hits:
        console.print(f"[{m.trust_tier} ~{score:.2f}] {m.content}  [dim]{m.id}[/]")


@user_app.command("observe")
def user_observe(
    text: str,
    user: str = typer.Option(_DEFAULT_USER, "--user", help="User ref"),
) -> None:
    """Propose an observation about the user (verified through the pipeline)."""
    from milyonus.config.env import load_env

    load_env()
    model = _model(user, with_pipeline=True)
    state = asyncio.run(model.observe(text))
    color = {"active": PALETTE["ok"], "rejected": PALETTE["risk"]}.get(state, PALETTE["warn"])
    console.print(f"[{color}]{GLYPH} {state}[/] — {text}")
