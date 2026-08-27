"""`milyonus proactive ...` — the scheduler runtime and automation suggestions."""

from __future__ import annotations

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE

proactive_app = typer.Typer(help="Proactivity: run the scheduler, suggest automations.")
console = Console()


@proactive_app.command("start")
def proactive_start(
    workspace: str = typer.Option(".", help="Agent working root"),
    poll: float = typer.Option(30.0, help="Poll interval (seconds)"),
) -> None:
    """Run the scheduler (long-lived). Fires due tasks and delivers results.

    This process must stay running (VPS/systemd) for 24/7 behavior — that is an
    infrastructure choice, not agent magic.
    """
    import asyncio
    import logging
    from pathlib import Path

    from milyonus.config.env import load_env
    from milyonus.config.loader import load_config
    from milyonus.cron.store import CronTask
    from milyonus.observability.trace import RunTrace
    from milyonus.proactive.scheduler import Scheduler
    from milyonus.providers.router import build_provider

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_env()
    cfg = load_config()
    provider = build_provider(cfg.provider)

    async def deliver(task: CronTask, answer: str, trace: RunTrace, denied: list[str]) -> None:
        console.print(
            f"\n[{PALETTE['cyan_400']}]{GLYPH} {task.name}[/] "
            f"[dim]({trace.total_tokens} tok)[/]\n{answer}"
        )
        if denied:
            console.print(f"[{PALETTE['warn']}]denied (safe-only): {', '.join(denied)}[/]")

    sched = Scheduler(
        provider, workspace=Path(workspace).resolve(), deliver=deliver, poll_seconds=poll
    )
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Scheduler[/] "
        f"[dim]polling every {poll:.0f}s · Ctrl+C to stop[/]"
    )
    try:
        asyncio.run(sched.run())
    except KeyboardInterrupt:
        console.print(f"\n[{PALETTE['chrome_500']}]Scheduler stopped.[/]")


@proactive_app.command("suggest")
def proactive_suggest() -> None:
    """Analyze history and suggest automations (repetition, not prediction).

    Suggestions are never auto-applied — turn one into a task with `milyonus cron add`.
    """
    from milyonus.core.store import SessionStore
    from milyonus.proactive.suggest import suggest_automations

    store = SessionStore()
    suggestions = suggest_automations(store)
    if not suggestions:
        console.print(f"[dim]{GLYPH} no recurring patterns found yet.[/]")
        raise typer.Exit()
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Automation suggestions[/] "
        f"[dim](based on repeated requests)[/]"
    )
    for s in suggestions:
        icon = "⏰" if s.kind == "schedule" else "✦"
        console.print(f"  {icon} {s.as_line()}")
    console.print("\n[dim]Create one with: milyonus cron add <name> <when> <prompt>[/]")
