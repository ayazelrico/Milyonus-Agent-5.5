"""`milyonus gateway ...` and `milyonus pair ...` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE
from milyonus.config.env import load_env
from milyonus.config.loader import load_config
from milyonus.gateway.pairing import PairingManager

gateway_app = typer.Typer(help="Manage the messaging gateway.")
console = Console()


@gateway_app.command("start")
def gateway_start(
    channel: str = typer.Option(
        "telegram", help="Channel to start: telegram|whatsapp|slack|discord"
    ),
    workspace: str = typer.Option(".", help="Agent working root"),
    port: int = typer.Option(8080, help="WhatsApp webhook port"),
) -> None:
    """Start the messaging gateway."""
    import asyncio
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_env()
    cfg = load_config()
    if cfg.security.gateway_allow_all_users:
        console.print(
            f"[{PALETTE['risk']}]UYARI: gateway_allow_all_users=true — "
            f"anyone can reach the bot. Disable in production![/]"
        )
    if channel == "telegram":
        from milyonus.gateway.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter()
        detail = "long-polling"
    elif channel == "whatsapp":
        from milyonus.gateway.adapters.whatsapp import WhatsAppCloudAdapter

        adapter = WhatsAppCloudAdapter(port=port)
        detail = f"Cloud API webhook :{port}"
    elif channel == "slack":
        from milyonus.gateway.adapters.slack import SlackAdapter

        adapter = SlackAdapter(port=port)
        detail = f"Events API webhook :{port}"
    elif channel == "discord":
        from milyonus.gateway.adapters.discord import DiscordAdapter

        adapter = DiscordAdapter()
        detail = "Gateway WebSocket"
    else:
        console.print(f"[{PALETTE['risk']}]Unsupported channel: {channel}[/]")
        raise typer.Exit(code=1)

    from milyonus.gateway.server import GatewayServer

    server = GatewayServer(cfg, [adapter], workspace=Path(workspace).resolve())
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Gateway[/] "
        f"[dim]{channel} · {detail} · default: deny (pairing required)[/]"
    )
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        console.print(f"\n[{PALETTE['chrome_500']}]Gateway stopped.[/]")


@gateway_app.command("pair")
def gateway_pair(channel: str = typer.Argument("telegram")) -> None:
    """Generate a new pairing code (valid for 1 hour)."""
    pm = PairingManager()
    code = pm.new_code(channel)
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Pairing code ({channel}):[/] [bold]{code}[/]"
    )
    console.print(f"[dim]Have the user send `/pair {code}` to the bot. Code valid for 1 hour.[/]")
