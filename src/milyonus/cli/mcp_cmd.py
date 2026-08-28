"""`milyonus mcp ...` — inspect configured MCP servers and their tools.

These commands answer "which external servers am I wired to, and what can they
do?" without starting a full session. They read the same `config.mcp_servers`
the agent uses, so what you see here is exactly what the model would be offered.
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from milyonus.brand import GLYPH, PALETTE

mcp_app = typer.Typer(help="Inspect external MCP servers.")
console = Console()


@mcp_app.command("list")
def mcp_list() -> None:
    """List the MCP servers declared in config (without connecting)."""
    from milyonus.config.loader import load_config

    cfg = load_config()
    if not cfg.mcp_servers:
        console.print(
            f"[dim]{GLYPH} no MCP servers configured.[/]\n"
            r"Add one under \[\[mcp_servers]] in ~/.milyonus/config.toml — "
            "see `milyonus mcp example`."
        )
        raise typer.Exit()
    table = Table(title=f"{GLYPH} MCP Servers")
    table.add_column("Name")
    table.add_column("Enabled")
    table.add_column("Risk")
    table.add_column("Command", overflow="fold")
    for s in cfg.mcp_servers:
        on = f"[{PALETTE['ok']}]yes[/]" if s.enabled else f"[{PALETTE['chrome_500']}]no[/]"
        table.add_row(s.name, on, s.risk, " ".join(s.command))
    console.print(table)


@mcp_app.command("tools")
def mcp_tools(
    name: str = typer.Argument(None, help="Only this server (default: all enabled)."),
) -> None:
    """Connect to the configured server(s) and list the tools they expose."""
    from milyonus.config.env import load_env
    from milyonus.config.loader import load_config
    from milyonus.tools.mcp.manager import MCPManager

    load_env()
    cfg = load_config()
    servers = [s for s in cfg.mcp_servers if name is None or s.name == name]
    if not servers:
        console.print(f"[{PALETTE['warn']}]{GLYPH} no matching MCP server configured.[/]")
        raise typer.Exit(code=1)

    manager = MCPManager(servers)
    asyncio.run(manager.start())

    for s in servers:
        tools = manager.connected.get(s.name)
        if tools is None:
            err = manager.errors.get(s.name, "not connected")
            console.print(f"[{PALETTE['risk']}]✗ {s.name}[/] — {err}")
            continue
        console.print(f"[bold {PALETTE['cyan_400']}]{GLYPH} {s.name}[/] ({len(tools)} tools)")
        for t in tools:
            console.print(f"  [{PALETTE['blue_500']}]{t}[/]")

    asyncio.run(manager.close())


@mcp_app.command("example")
def mcp_example() -> None:
    """Print a ready-to-paste config.toml block for an MCP server."""
    console.print(f"[dim]{GLYPH} add to ~/.milyonus/config.toml:[/]\n")
    block = (
        "[[mcp_servers]]\n"
        'name = "github"\n'
        'command = ["npx", "-y", "@modelcontextprotocol/server-github"]\n'
        "enabled = true\n"
        'risk = "caution"                    # tools gated by the RiskEngine\n'
        'env_passthrough = ["GITHUB_TOKEN"]  # grant just this server its key'
    )
    # markup=False so rich does not eat the TOML's [[...]] as style tags.
    console.print(block, markup=False, highlight=False)
