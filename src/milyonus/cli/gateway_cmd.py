"""`milyonus gateway ...` and `milyonus pair ...` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE
from milyonus.config.env import load_env
from milyonus.config.loader import load_config
from milyonus.gateway.pairing import PairingManager

gateway_app = typer.Typer(help="Mesajlaşma gateway'ini yönet.")
console = Console()


@gateway_app.command("start")
def gateway_start(
    channel: str = typer.Option("telegram", help="Başlatılacak kanal: telegram|whatsapp"),
    workspace: str = typer.Option(".", help="Agent çalışma kökü"),
    port: int = typer.Option(8080, help="WhatsApp webhook portu"),
) -> None:
    """Mesajlaşma gateway'ini başlat."""
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
            f"herkes bota erişebilir. Üretimde kapatın![/]"
        )
    if channel == "telegram":
        from milyonus.gateway.adapters.telegram import TelegramAdapter

        adapter = TelegramAdapter()
        detail = "long-polling"
    elif channel == "whatsapp":
        from milyonus.gateway.adapters.whatsapp import WhatsAppCloudAdapter

        adapter = WhatsAppCloudAdapter(port=port)
        detail = f"Cloud API webhook :{port}"
    else:
        console.print(f"[{PALETTE['risk']}]Desteklenmeyen kanal: {channel}[/]")
        raise typer.Exit(code=1)

    from milyonus.gateway.server import GatewayServer

    server = GatewayServer(cfg, [adapter], workspace=Path(workspace).resolve())
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Gateway[/] "
        f"[dim]{channel} · {detail} · varsayılan: reddet (pairing gerekli)[/]"
    )
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        console.print(f"\n[{PALETTE['chrome_500']}]Gateway durduruldu.[/]")


@gateway_app.command("pair")
def gateway_pair(channel: str = typer.Argument("telegram")) -> None:
    """Yeni bir eşleştirme kodu üret (1 saat geçerli)."""
    pm = PairingManager()
    code = pm.new_code(channel)
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Eşleştirme kodu ({channel}):[/] [bold]{code}[/]"
    )
    console.print(f"[dim]Kullanıcı botta `/pair {code}` göndersin. Kod 1 saat geçerli.[/]")
