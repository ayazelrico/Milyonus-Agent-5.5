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

app = typer.Typer(
    name="milyonus",
    help=f"{GLYPH} {PRODUCT} — remembers, verifies, evolves.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(
            f"[bold {PALETTE['cyan_400']}]{GLYPH} {PRODUCT}[/] "
            f"[{PALETTE['chrome_200']}]v{__version__}[/]"
        )
        raise typer.Exit()


@app.callback()
def _main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """Milyonus Agent command-line interface. Starts an interactive session
    when called with no arguments."""
    # No subcommand -> start the interactive session (the default surface).
    if ctx.invoked_subcommand is None:
        from milyonus.cli.tui import run_tui

        raise typer.Exit(code=run_tui())


@app.command()
def doctor() -> None:
    """Run environment and health diagnostics."""
    from milyonus.cli.doctor import run_doctor

    raise typer.Exit(code=run_doctor())


@app.command()
def setup() -> None:
    """First-run setup wizard: provider and key."""
    from milyonus.cli.setup import run_setup

    raise typer.Exit(code=run_setup())


@app.command()
def acp() -> None:
    """Run as an ACP server (editor integration, stdio/JSON-RPC)."""
    import asyncio

    from milyonus.acp.server import run_stdio
    from milyonus.config.env import load_env
    from milyonus.config.loader import load_config

    load_env()
    asyncio.run(run_stdio(load_config()))


@app.command()
def chat() -> None:
    """Start an interactive terminal session (same as bare `milyonus`)."""
    from milyonus.cli.tui import run_tui

    raise typer.Exit(code=run_tui())


from milyonus.cli.eval_cmd import eval_app  # noqa: E402
from milyonus.cli.gateway_cmd import gateway_app  # noqa: E402
from milyonus.cli.memory_cmd import audit_app, memory_app  # noqa: E402
from milyonus.cli.selfmod_cmd import selfmod_app  # noqa: E402
from milyonus.cli.skills_cmd import skills_app  # noqa: E402

app.add_typer(memory_app, name="memory")
app.add_typer(audit_app, name="audit")
app.add_typer(skills_app, name="skills")
app.add_typer(gateway_app, name="gateway")
app.add_typer(selfmod_app, name="selfmod")
app.add_typer(eval_app, name="eval")


def main() -> None:
    """console_scripts entry point."""
    app()


if __name__ == "__main__":
    main()
