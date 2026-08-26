"""`milyonus skills ...` — inspect and manage skills from the terminal."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from milyonus.brand import GLYPH, PALETTE
from milyonus.skills.engine import SkillEngine

skills_app = typer.Typer(help="Skill'leri görüntüle ve yönet.")
console = Console()


@skills_app.command("list")
def skills_list() -> None:
    """Kayıtlı skill'leri listele."""
    eng = SkillEngine()
    skills = eng.load_all()
    if not skills:
        console.print(f"[dim]{GLYPH} kayıtlı skill yok.[/]")
        raise typer.Exit()
    table = Table(title=f"{GLYPH} Skill'ler")
    table.add_column("Ad", style=f"bold {PALETTE['cyan_400']}")
    table.add_column("Kategori")
    table.add_column("Açıklama", overflow="fold")
    table.add_column("Kaynak", style="dim")
    table.add_column("Sürüm", style="dim")
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
    """Bir skill'in içeriğini göster."""
    eng = SkillEngine()
    console.print(eng.view(name, ref))


@skills_app.command("why")
def skills_why(name: str) -> None:
    """Bir skill'in kökenini (provenance) göster."""
    eng = SkillEngine()
    skill = eng.get(name)
    if skill is None:
        console.print(f"[{PALETTE['risk']}]bulunamadı: {name}[/]")
        raise typer.Exit(code=1)
    m = skill.meta
    console.print(f"[bold]{GLYPH} {m.name}[/] v{m.version}")
    console.print(f"  kaynak    : {m.provenance}")
    console.print(f"  kategori  : {m.category}")
    console.print(f"  platformlar: {', '.join(m.platforms) or 'tümü'}")
    console.print(f"  yol       : {skill.path}")
    refs = skill.reference_files()
    if refs:
        console.print(f"  referanslar: {', '.join(refs)}")
