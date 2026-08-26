"""Milyonus CLI entry point.

This is the single binary users invoke as `milyonus` (alias `mil`). In F0 it
exposes the first live surface: version, banner, and `doctor`. Later phases add
`run`, `setup`, `memory`, `skills`, `gateway`, `cron`, `selfmod`, and `audit`
as subcommands on this same app.
"""

from __future__ import annotations

import typer
from rich.console import Console

from milyonus import __version__
from milyonus.brand import GLYPH, PALETTE, PRODUCT
from milyonus.version import CODENAME

app = typer.Typer(
    name="milyonus",
    help=f"{GLYPH} {PRODUCT} — remembers, verifies, evolves.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(
            f"[bold {PALETTE['cyan_400']}]{GLYPH} {PRODUCT}[/] "
            f"[{PALETTE['chrome_200']}]v{__version__}[/] "
            f"[dim](codename {CODENAME})[/]"
        )
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Sürümü göster ve çık.",
    ),
) -> None:
    """Milyonus Agent command-line interface."""


@app.command()
def doctor() -> None:
    """Ortam ve sağlık teşhisi çalıştır."""
    from milyonus.cli.doctor import run_doctor

    raise typer.Exit(code=run_doctor())


def main() -> None:
    """console_scripts entry point."""
    app()


if __name__ == "__main__":
    main()
