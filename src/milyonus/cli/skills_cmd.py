"""`milyonus skills ...` — inspect and manage skills from the terminal."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from milyonus.brand import GLYPH, PALETTE
from milyonus.skills.engine import SkillEngine

skills_app = typer.Typer(help="Inspect and manage skills.")
console = Console()


@skills_app.command("list")
def skills_list() -> None:
    """List registered skills."""
    eng = SkillEngine()
    skills = eng.load_all()
    if not skills:
        console.print(f"[dim]{GLYPH} no registered skills.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Skills")
    table.add_column("Name", style=f"bold {PALETTE['cyan_400']}")
    table.add_column("Category")
    table.add_column("Description", overflow="fold")
    table.add_column("Source", style="dim")
    table.add_column("Version", style="dim")
    for s in skills:
        table.add_row(
            s.meta.name,
            s.meta.category,
            s.meta.description,
            s.meta.provenance,
            s.meta.version,
        )
    console.print(table)


@skills_app.command("view")
def skills_view(name: str, ref: str = typer.Argument(None)) -> None:
    """Show a skill's content."""
    eng = SkillEngine()
    console.print(eng.view(name, ref))


@skills_app.command("why")
def skills_why(name: str) -> None:
    """Show a skill's provenance."""
    eng = SkillEngine()
    skill = eng.get(name)
    if skill is None:
        console.print(f"[{PALETTE['risk']}]not found: {name}[/]")
        raise typer.Exit(code=1)
    m = skill.meta
    console.print(f"[bold]{GLYPH} {m.name}[/] v{m.version}")
    console.print(f"  source    : {m.provenance}")
    console.print(f"  category  : {m.category}")
    console.print(f"  platforms : {', '.join(m.platforms) or 'all'}")
    console.print(f"  path      : {skill.path}")
    refs = skill.reference_files()
    if refs:
        console.print(f"  references: {', '.join(refs)}")
