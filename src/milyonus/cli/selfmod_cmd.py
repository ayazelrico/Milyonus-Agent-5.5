"""`milyonus selfmod ...` — inspect and roll back self-modifications."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE
from milyonus.selfmod.harness import SelfModHarness

selfmod_app = typer.Typer(help="Manage self-modification snapshots.")
console = Console()


@selfmod_app.command("log")
def selfmod_log() -> None:
    """List self-modification snapshots."""
    h = SelfModHarness(Path.cwd())
    if not h.is_git_repo():
        console.print(f"[{PALETTE['warn']}]This directory is not a git repo.[/]")
        raise typer.Exit(code=1)
    entries = h.log()
    if not entries:
        console.print(f"[dim]{GLYPH} no self-modifications.[/]")
        raise typer.Exit()
    console.print(f"[bold]{GLYPH} Selfmod snapshots[/]")
    for e in entries:
        console.print(f"  {e}")


@selfmod_app.command("rollback")
def selfmod_rollback(
    ref: str = typer.Argument("HEAD~1", help="Commit/tag to roll back to"),
) -> None:
    """Roll back to the previous (or given) snapshot."""
    h = SelfModHarness(Path.cwd())
    result = h.rollback(ref)
    console.print(f"[{PALETTE['quarantine']}]{GLYPH} {result}[/]")
