"""`milyonus setup` — a short first-run wizard.

Writes ~/.milyonus/config.toml (provider + model choice) and reminds the user to
place their key in ~/.milyonus/.env. It never asks for the key on the command
line — secrets go in the .env file the user controls (PLAN §6 layer 4).
"""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt

from milyonus.brand import GLYPH, PALETTE
from milyonus.config.paths import config_file, ensure_layout, env_file

console = Console()

# Per-provider: the key env var, a default main model, a cheap verifier model,
# and a few suggestions to show the user.
_PROVIDERS = {
    "anthropic": {
        "key": "ANTHROPIC_API_KEY",
        "model": "claude-opus-4-8",
        "verifier": "claude-haiku-4-5-20251001",
        "suggest": ["claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
    },
    "openai": {
        "key": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "verifier": "gpt-4o-mini",
        "suggest": ["gpt-4o", "gpt-4o-mini"],
    },
    "openrouter": {
        "key": "OPENROUTER_API_KEY",
        "model": "anthropic/claude-sonnet-4.5",
        "verifier": "anthropic/claude-haiku-4.5",
        "suggest": ["anthropic/claude-opus-4.8", "anthropic/claude-sonnet-4.5", "openai/gpt-4o"],
    },
    "local": {
        "key": None,
        "model": "llama3",
        "verifier": "llama3",
        "suggest": ["llama3", "qwen2.5", "mistral"],
    },
}


def _toml_str(v: str) -> str:
    return '"' + v.replace('"', '\\"') + '"'


def run_setup() -> int:
    ensure_layout()
    console.print(f"[bold {PALETTE['cyan_400']}]{GLYPH} Milyonus setup[/]\n")

    provider = Prompt.ask(
        "Provider",
        choices=list(_PROVIDERS),
        default="anthropic",
    )
    spec = _PROVIDERS[provider]

    # Model selection — the piece that was missing.
    console.print(f"[dim]suggestions: {', '.join(spec['suggest'])}[/]")
    model = Prompt.ask("Model", default=spec["model"])
    verifier = Prompt.ask(
        "Verifier model [dim](cheap; gates memory promotion)[/]",
        default=spec["verifier"],
    )

    # Build the config body.
    lines = ["[provider]"]
    if provider == "openrouter":
        # OpenRouter is the openai provider pointed at a different base_url.
        lines += [
            'name = "openai"',
            'base_url = "https://openrouter.ai/api/v1"',
            'api_key_env = "OPENROUTER_API_KEY"',
        ]
    else:
        lines.append(f"name = {_toml_str(provider)}")
    lines.append(f"model = {_toml_str(model)}")
    lines.append(f"verifier_model = {_toml_str(verifier)}")
    body = "\n".join(lines) + "\n"

    path = config_file()
    path.write_text(body, encoding="utf-8")
    console.print(f"\n[{PALETTE['ok']}]wrote:[/] {path}")
    console.print(f"  provider [bold]{provider}[/] · model [bold]{model}[/] · verifier {verifier}")

    key = spec["key"]
    if key:
        console.print(
            f"\n[bold]Next step[/] — add your key (nobody sees the value):\n"
            f"  [dim]echo '{key}=...' >> {env_file()} && chmod 600 {env_file()}[/]"
        )
    else:
        console.print(
            "\n[dim]Local provider needs no key. Make sure your server (Ollama/vLLM) is running.[/]"
        )
    console.print("\nThen: verify with [bold]milyonus doctor[/], start with [bold]milyonus[/].")
    return 0
