"""`milyonus doctor` — environment and health diagnostics.

The first real command a user runs after install. It checks the things that
silently break an agent later: Python version, data layout, config validity,
provider credentials, and directory permissions. It never mutates state beyond
creating the data layout, and it never prints secret values.
"""

from __future__ import annotations

import os
import platform
import stat
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from milyonus import __version__
from milyonus.brand import GLYPH, PALETTE
from milyonus.config.env import env_file_is_private, load_env
from milyonus.config.loader import ConfigError, load_config
from milyonus.config.paths import config_file, ensure_layout, env_file


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _python_check() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 12)
    return Check("Python", ok, f"{v.major}.{v.minor}.{v.micro} (>=3.12 required)")


def _layout_check() -> Check:
    root = ensure_layout()
    mode = stat.S_IMODE(root.stat().st_mode)
    ok = mode == 0o700
    detail = f"{root} (mode {oct(mode)}; 0o700 recommended)"
    return Check("Data dir", ok, detail)


def _config_check() -> Check:
    path = config_file()
    if not path.exists():
        return Check("Config", True, f"{path} missing — using defaults")
    try:
        load_config(path)
        return Check("Config", True, f"{path} valid")
    except ConfigError as exc:
        first = str(exc).splitlines()[0]
        return Check("Config", False, first)


def _env_check() -> Check:
    private = env_file_is_private()
    if private is None:
        return Check("Secret file", True, f"{env_file()} missing (optional)")
    if not private:
        return Check(
            "Secret file",
            False,
            f"{env_file()} too open — run `chmod 600`",
        )
    return Check("Secret file", True, f"{env_file()} (mode 0600)")


def _provider_check() -> Check:
    try:
        cfg = load_config()
    except ConfigError:
        return Check("Provider", False, "could not read config")
    name = cfg.provider.name
    env_key = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "local": None,
    }[name]
    if env_key is None:
        return Check("Provider", True, f"{name} (local — no key required)")
    present = bool(os.environ.get(env_key))
    detail = f"{name} · {env_key} {'found' if present else 'NOT SET'}"
    return Check("Provider", present, detail)


def run_doctor() -> int:
    """Run all checks, print a table, return process exit code (0 = all ok)."""
    console = Console()
    load_env()  # pull ~/.milyonus/.env into the environment before checking keys
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Milyonus doctor[/] "
        f"[dim]v{__version__} · {platform.system()} {platform.machine()}[/]"
    )

    checks = [
        _python_check(),
        _layout_check(),
        _config_check(),
        _env_check(),
        _provider_check(),
    ]

    table = Table(show_header=True, header_style=f"bold {PALETTE['chrome_200']}")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")
    for c in checks:
        badge = f"[{PALETTE['ok']}]● ok[/]" if c.ok else f"[{PALETTE['risk']}]● issue[/]"
        table.add_row(c.name, badge, c.detail)
    console.print(table)

    failed = [c for c in checks if not c.ok]
    if failed:
        console.print(
            f"[{PALETTE['warn']}]{len(failed)} check(s) need attention.[/] "
            "Run `milyonus setup` to configure a provider key."
        )
        return 1
    console.print(f"[{PALETTE['ok']}]All good.[/]")
    return 0
