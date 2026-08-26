"""`milyonus setup` — a short first-run wizard.

Writes ~/.milyonus/config.toml (provider choice) and reminds the user to place
their key in ~/.milyonus/.env. It never asks for the key on the command line —
secrets go in the .env file the user controls (PLAN §6 layer 4).
"""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt

from milyonus.brand import GLYPH, PALETTE
from milyonus.config.paths import config_file, ensure_layout, env_file

console = Console()

_PROVIDER_KEY = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "local": None,
}


def run_setup() -> int:
    ensure_layout()
    console.print(f"[bold {PALETTE['cyan_400']}]{GLYPH} Milyonus kurulum[/]\n")

    provider = Prompt.ask(
        "Sağlayıcı",
        choices=["anthropic", "openai", "openrouter", "local"],
        default="anthropic",
    )

    # Map openrouter to the openai provider with a base_url.
    if provider == "openrouter":
        body = (
            '[provider]\nname = "openai"\n'
            'base_url = "https://openrouter.ai/api/v1"\n'
            'api_key_env = "OPENROUTER_API_KEY"\n'
        )
    elif provider == "local":
        model = Prompt.ask("Yerel model adı", default="llama3")
        body = f'[provider]\nname = "local"\nmodel = "{model}"\n'
    else:
        body = f'[provider]\nname = "{provider}"\n'

    path = config_file()
    path.write_text(body, encoding="utf-8")
    console.print(f"[{PALETTE['ok']}]yazıldı:[/] {path}")

    key = _PROVIDER_KEY[provider]
    if key:
        console.print(
            f"\n[bold]Sıradaki adım[/] — anahtarını ekle (değeri kimse görmez):\n"
            f"  [dim]echo '{key}=...' >> {env_file()} && chmod 600 {env_file()}[/]"
        )
    console.print("\nSonra: [bold]milyonus doctor[/] ile doğrula, [bold]milyonus[/] ile başla.")
    return 0
