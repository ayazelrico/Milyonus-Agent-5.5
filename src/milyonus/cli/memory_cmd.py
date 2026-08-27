"""`milyonus memory ...` and `milyonus audit ...` commands.

These are the answer to "who wrote this memory and was it verified?" (PLAN §4.8).
Every command reads the same store the agent uses, so provenance is always one
command away.
"""

from __future__ import annotations

import time

import typer
from rich.console import Console
from rich.table import Table

from milyonus.brand import GLYPH, PALETTE
from milyonus.memory.store import MemoryStore

memory_app = typer.Typer(help="Inspect and manage verified memory.")
audit_app = typer.Typer(help="Verify the audit ledger.")
console = Console()

_TIER_COLOR = {
    "T0": PALETTE["chrome_200"],
    "T1": PALETTE["ok"],
    "T2": PALETTE["cyan_400"],
    "T3": PALETTE["warn"],
    "T4": PALETTE["quarantine"],
}


def _age(ts: float) -> str:
    secs = time.time() - ts
    if secs < 3600:
        return f"{int(secs // 60)}dk"
    if secs < 86400:
        return f"{int(secs // 3600)}sa"
    return f"{int(secs // 86400)}g"


@memory_app.command("list")
def memory_list() -> None:
    """List verified (active) durable memory."""
    store = MemoryStore()
    items = store.active()
    if not items:
        console.print(f"[dim]{GLYPH} durable memory is empty.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Durable Memory")
    table.add_column("Tier")
    table.add_column("Content", overflow="fold")
    table.add_column("Source")
    table.add_column("Age")
    table.add_column("id", style="dim")
    for m in items:
        color = _TIER_COLOR.get(m.trust_tier, "white")
        table.add_row(
            f"[{color}]{m.trust_tier}[/]",
            m.content,
            m.provenance.source_kind,
            _age(m.created_at),
            m.id,
        )
    console.print(table)


@memory_app.command("pending")
def memory_pending() -> None:
    """Show candidates pending in quarantine."""
    store = MemoryStore()
    items = store.by_state("pending")
    if not items:
        console.print(f"[dim]{GLYPH} quarantine is empty.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Quarantine (pending)")
    table.add_column("Tier")
    table.add_column("Content", overflow="fold")
    table.add_column("Source")
    table.add_column("Confirms")
    table.add_column("id", style="dim")
    for m in items:
        table.add_row(
            m.trust_tier,
            m.content,
            m.provenance.source_kind,
            str(m.confirmations),
            m.id,
        )
    console.print(table)


@memory_app.command("why")
def memory_why(item_id: str) -> None:
    """Show a memory's full provenance chain."""
    store = MemoryStore()
    m = store.get(item_id)
    if m is None:
        console.print(f"[{PALETTE['risk']}]Not found: {item_id}[/]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{GLYPH} {m.id}[/]  [dim]{m.state}[/]")
    console.print(f"  content  : {m.content}")
    console.print(f"  tier     : {m.trust_tier}")
    console.print(f"  source   : {m.provenance.source_kind} {m.provenance.source_uri or ''}")
    console.print(f"  session  : {m.provenance.session_id} / turn {m.provenance.turn_id}")
    console.print(f"  actor    : {m.provenance.actor or '-'}")
    console.print(f"  evidence#: {m.evidence_hash}")
    console.print(f"  verdict  : {m.verdict or '-'}")
    console.print(f"  confirms : {m.confirmations}")
    console.print(f"  trust    : {m.trust_score:.2f}  (reaffirmed {m.reaffirm_count}×)")


@memory_app.command("diff")
def memory_diff(since: str = typer.Option("7d", help="e.g. 24h, 7d")) -> None:
    """What was learned/changed within the given window."""
    store = MemoryStore()
    unit = since[-1]
    value = int(since[:-1])
    seconds = value * {"h": 3600, "d": 86400}.get(unit, 86400)
    cutoff = time.time() - seconds
    recent = [m for m in store.active() if m.created_at >= cutoff]
    console.print(f"[bold]{GLYPH} {len(recent)} new memories in the last {since}[/]")
    for m in recent:
        console.print(f"  [{m.trust_tier}] {m.content}  [dim]{m.id}[/]")


@memory_app.command("revoke")
def memory_revoke(
    source: str = typer.Option(..., "--source", help="Source URI to revoke"),
) -> None:
    """Revoke all memory derived from a source (cascade)."""
    store = MemoryStore()
    revoked = store.revoke_by_source(source)
    console.print(
        f"[{PALETTE['quarantine']}]{GLYPH} revoked {len(revoked)} memories[/] (source: {source})"
    )
    for rid in revoked:
        console.print(f"  - {rid}")


@memory_app.command("search")
def memory_search(query: str) -> None:
    """Search content in active memory."""
    store = MemoryStore()
    q = query.casefold()
    hits = [m for m in store.active() if q in m.content.casefold()]
    if not hits:
        console.print("[dim]no matches[/]")
        raise typer.Exit()
    for m in hits:
        console.print(f"[{m.trust_tier}] {m.content}  [dim]{m.id}[/]")


@audit_app.command("verify")
def audit_verify() -> None:
    """Verify the memory audit ledger's hash chain."""
    store = MemoryStore()
    ok = store.verify_ledger()
    if ok:
        console.print(f"[{PALETTE['ok']}]{GLYPH} audit ledger integrity intact.[/]")
    else:
        console.print(f"[{PALETTE['risk']}]{GLYPH} WARNING: audit ledger tampered![/]")
        raise typer.Exit(code=1)


@audit_app.command("log")
def audit_log(limit: int = 30) -> None:
    """Show recent audit ledger entries."""
    store = MemoryStore()
    entries = store.ledger_entries(limit=limit)
    table = Table(title=f"{GLYPH} Audit Ledger")
    table.add_column("seq")
    table.add_column("action")
    table.add_column("item", style="dim")
    table.add_column("hash", style="dim")
    for e in reversed(entries):
        table.add_row(str(e["seq"]), e["action"], e["item_id"] or "-", e["entry_hash"][:12])
    console.print(table)


@memory_app.command("consolidate")
def memory_consolidate() -> None:
    """Sleep-time consolidation: process pending, expire due, merge
    duplicates, flag contradictions."""
    import asyncio

    from milyonus.config.env import load_env
    from milyonus.config.loader import load_config
    from milyonus.memory.consolidate import consolidate
    from milyonus.memory.pipeline import MemoryPipeline

    load_env()
    cfg = load_config()
    store = MemoryStore()
    pipeline = MemoryPipeline(store, config=cfg.memory)
    report = asyncio.run(consolidate(pipeline))
    console.print(f"[bold {PALETTE['cyan_400']}]{GLYPH} Consolidation[/]")
    console.print(f"  {report.summary()}")
    for a, b in report.contradictions:
        console.print(f"  [{PALETTE['warn']}]contradiction:[/] {a} <-> {b}")


@memory_app.command("reaffirm")
def memory_reaffirm(item_id: str) -> None:
    """Re-earn full trust for a memory (resets its decay clock)."""
    import time

    from milyonus.config.loader import load_config
    from milyonus.memory.trust import review_at

    cfg = load_config()
    store = MemoryStore()
    m = store.get(item_id)
    if m is None:
        console.print(f"[{PALETTE['risk']}]not found: {item_id}[/]")
        raise typer.Exit(code=1)
    store.reaffirm(item_id, review_at=review_at(m.trust_tier, time.time(), cfg.memory))
    console.print(f"[{PALETTE['ok']}]{GLYPH} reaffirmed[/] {item_id} — trust reset to 1.00")
