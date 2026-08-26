"""`milyonus eval ...` — run the task-level evaluation suite (observability)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from milyonus.brand import GLYPH, PALETTE

eval_app = typer.Typer(help="Görev düzeyi değerlendirme ve gözlemlenebilirlik.")
console = Console()


@eval_app.command("run")
def eval_run() -> None:
    """TaskBench'i gerçek agent üzerinden çalıştır ve metrikleri raporla.

    Sağlayıcı anahtarı gerekir (canlı görevler). Her görev izole bir çalışma
    dizininde koşar, programatik olarak skorlanır ve üretim metrikleri toplanır.
    """
    import asyncio

    from milyonus.config.env import load_env
    from milyonus.config.loader import ConfigError, load_config
    from milyonus.evaluation.runner import run_task
    from milyonus.evaluation.tasks import TASKS
    from milyonus.observability.report import aggregate

    load_env()
    try:
        load_config()
    except ConfigError as exc:
        console.print(f"[{PALETTE['risk']}]Yapılandırma hatası:[/] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} TaskBench[/] "
        f"[dim]{len(TASKS)} görev çalıştırılıyor…[/]\n"
    )

    async def _all():
        traces = []
        for t in TASKS:
            tr = await run_task(t)
            badge = f"[{PALETTE['ok']}]✓[/]" if tr.success else f"[{PALETTE['risk']}]✗[/]"
            console.print(
                f"  {badge} [bold]{t.id}[/] [dim]{tr.outcome}[/] · "
                f"{tr.total_tokens} tok · {tr.n_tool_calls} araç · {tr.duration_s:.1f}s"
            )
            traces.append(tr)
        return traces

    traces = asyncio.run(_all())
    rep = aggregate(traces)

    table = Table(title=f"{GLYPH} Değerlendirme Raporu", show_header=False)
    table.add_column("Metrik", style=PALETTE["chrome_200"])
    table.add_column("Değer", justify="right")
    table.add_row("Görev", str(rep.n_tasks))
    table.add_row("  başarılı", f"[{PALETTE['ok']}]{rep.n_success}[/]")
    table.add_row("  başarısız", f"[{PALETTE['risk']}]{rep.n_fail}[/]")
    table.add_row("Başarı oranı", f"[bold]{rep.success_rate:.1%}[/]")
    table.add_row("Araç çağrısı", str(rep.tool_calls))
    table.add_row("  araç hatası", str(rep.tool_errors))
    table.add_row("  gereksiz çağrı", str(rep.redundant_tool_calls))
    table.add_row("Token (in/out)", f"{rep.input_tokens} / {rep.output_tokens}")
    table.add_row("Süre", f"{rep.minutes:.2f} dk")
    table.add_row("Maliyet", f"${rep.usd:.4f}{' (tahmini)' if rep.usd_estimated else ''}")
    table.add_row("Human intervention", str(rep.human_interventions))
    console.print()
    console.print(table)


@eval_app.command("tasks")
def eval_tasks() -> None:
    """Değerlendirme görevlerini listele (çalıştırmadan)."""
    from milyonus.evaluation.tasks import TASKS

    for t in TASKS:
        console.print(f"[{PALETTE['cyan_400']}]{t.category}[/] · [bold]{t.id}[/]: {t.prompt}")
