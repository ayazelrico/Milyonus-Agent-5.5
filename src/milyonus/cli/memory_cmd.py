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

memory_app = typer.Typer(help="Doğrulanmış belleği görüntüle ve yönet.")
audit_app = typer.Typer(help="Denetim günlüğünü doğrula.")
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
    """Doğrulanmış (aktif) kalıcı belleği listele."""
    store = MemoryStore()
    items = store.active()
    if not items:
        console.print(f"[dim]{GLYPH} kalıcı bellek boş.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Kalıcı Bellek")
    table.add_column("Katman")
    table.add_column("İçerik", overflow="fold")
    table.add_column("Kaynak")
    table.add_column("Yaş")
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
    """Karantinada bekleyen adayları göster."""
    store = MemoryStore()
    items = store.by_state("pending")
    if not items:
        console.print(f"[dim]{GLYPH} karantina boş.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Karantina (bekleyen)")
    table.add_column("Katman")
    table.add_column("İçerik", overflow="fold")
    table.add_column("Kaynak")
    table.add_column("Teyit")
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
    """Bir belleğin tam kaynak zincirini (provenance) göster."""
    store = MemoryStore()
    m = store.get(item_id)
    if m is None:
        console.print(f"[{PALETTE['risk']}]Bulunamadı: {item_id}[/]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{GLYPH} {m.id}[/]  [dim]{m.state}[/]")
    console.print(f"  içerik   : {m.content}")
    console.print(f"  katman   : {m.trust_tier}")
    console.print(f"  kaynak   : {m.provenance.source_kind} {m.provenance.source_uri or ''}")
    console.print(f"  oturum   : {m.provenance.session_id} / tur {m.provenance.turn_id}")
    console.print(f"  aktör    : {m.provenance.actor or '-'}")
    console.print(f"  kanıt#   : {m.evidence_hash}")
    console.print(f"  verdikt  : {m.verdict or '-'}")
    console.print(f"  teyit    : {m.confirmations}")


@memory_app.command("diff")
def memory_diff(since: str = typer.Option("7d", help="örn. 24h, 7d")) -> None:
    """Belirtilen süre içinde ne öğrenildi/değişti."""
    store = MemoryStore()
    unit = since[-1]
    value = int(since[:-1])
    seconds = value * {"h": 3600, "d": 86400}.get(unit, 86400)
    cutoff = time.time() - seconds
    recent = [m for m in store.active() if m.created_at >= cutoff]
    console.print(f"[bold]{GLYPH} Son {since} içinde {len(recent)} yeni bellek[/]")
    for m in recent:
        console.print(f"  [{m.trust_tier}] {m.content}  [dim]{m.id}[/]")


@memory_app.command("revoke")
def memory_revoke(
    source: str = typer.Option(..., "--source", help="İptal edilecek kaynak URI"),
) -> None:
    """Bir kaynaktan türeyen tüm bellekleri (kaskad) iptal et."""
    store = MemoryStore()
    revoked = store.revoke_by_source(source)
    console.print(
        f"[{PALETTE['quarantine']}]{GLYPH} {len(revoked)} bellek iptal edildi[/] (kaynak: {source})"
    )
    for rid in revoked:
        console.print(f"  - {rid}")


@memory_app.command("search")
def memory_search(query: str) -> None:
    """Aktif bellekte içerik ara."""
    store = MemoryStore()
    q = query.casefold()
    hits = [m for m in store.active() if q in m.content.casefold()]
    if not hits:
        console.print("[dim]eşleşme yok[/]")
        raise typer.Exit()
    for m in hits:
        console.print(f"[{m.trust_tier}] {m.content}  [dim]{m.id}[/]")


@audit_app.command("verify")
def audit_verify() -> None:
    """Bellek denetim günlüğünün hash zincirini doğrula."""
    store = MemoryStore()
    ok = store.verify_ledger()
    if ok:
        console.print(f"[{PALETTE['ok']}]{GLYPH} denetim günlüğü bütünlüğü sağlam.[/]")
    else:
        console.print(f"[{PALETTE['risk']}]{GLYPH} UYARI: denetim günlüğü kurcalanmış![/]")
        raise typer.Exit(code=1)


@audit_app.command("log")
def audit_log(limit: int = 30) -> None:
    """Son denetim günlüğü girdilerini göster."""
    store = MemoryStore()
    entries = store.ledger_entries(limit=limit)
    table = Table(title=f"{GLYPH} Denetim Günlüğü")
    table.add_column("seq")
    table.add_column("eylem")
    table.add_column("item", style="dim")
    table.add_column("hash", style="dim")
    for e in reversed(entries):
        table.add_row(str(e["seq"]), e["action"], e["item_id"] or "-", e["entry_hash"][:12])
    console.print(table)
