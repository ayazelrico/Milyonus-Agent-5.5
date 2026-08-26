"""`milyonus selfmod ...` — inspect and roll back self-modifications."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE
from milyonus.selfmod.harness import SelfModHarness

selfmod_app = typer.Typer(help="Kendini değiştirme anlık görüntülerini yönet.")
console = Console()


@selfmod_app.command("log")
def selfmod_log() -> None:
    """Kendi kendine yapılan değişiklik anlık görüntülerini listele."""
    h = SelfModHarness(Path.cwd())
    if not h.is_git_repo():
        console.print(f"[{PALETTE['warn']}]Bu dizin bir git deposu değil.[/]")
        raise typer.Exit(code=1)
    entries = h.log()
    if not entries:
        console.print(f"[dim]{GLYPH} kendi kendine değişiklik yok.[/]")
        raise typer.Exit()
    console.print(f"[bold]{GLYPH} Selfmod anlık görüntüleri[/]")
    for e in entries:
        console.print(f"  {e}")


@selfmod_app.command("rollback")
def selfmod_rollback(
    ref: str = typer.Argument("HEAD~1", help="Geri dönülecek commit/etiket"),
) -> None:
    """Bir önceki (veya belirtilen) anlık görüntüye geri dön."""
    h = SelfModHarness(Path.cwd())
    result = h.rollback(ref)
    console.print(f"[{PALETTE['quarantine']}]{GLYPH} {result}[/]")
