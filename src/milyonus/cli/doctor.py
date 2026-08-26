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
from milyonus.config.loader import ConfigError, load_config
from milyonus.config.paths import config_file, ensure_layout


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _python_check() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 12)
    return Check("Python", ok, f"{v.major}.{v.minor}.{v.micro} (>=3.12 gerekli)")


def _layout_check() -> Check:
    root = ensure_layout()
    mode = stat.S_IMODE(root.stat().st_mode)
    ok = mode == 0o700
    detail = f"{root} (mod {oct(mode)}; 0o700 önerilir)"
    return Check("Veri dizini", ok, detail)


def _config_check() -> Check:
    path = config_file()
    if not path.exists():
        return Check("Yapılandırma", True, f"{path} yok — varsayılanlar kullanılıyor")
    try:
        load_config(path)
        return Check("Yapılandırma", True, f"{path} geçerli")
    except ConfigError as exc:
        first = str(exc).splitlines()[0]
        return Check("Yapılandırma", False, first)


def _provider_check() -> Check:
    try:
        cfg = load_config()
    except ConfigError:
        return Check("Sağlayıcı", False, "yapılandırma okunamadı")
    name = cfg.provider.name
    env_key = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "local": None,
    }[name]
    if env_key is None:
        return Check("Sağlayıcı", True, f"{name} (yerel — anahtar gerekmez)")
    present = bool(os.environ.get(env_key))
    detail = f"{name} · {env_key} {'bulundu' if present else 'AYARLANMAMIŞ'}"
    return Check("Sağlayıcı", present, detail)


def run_doctor() -> int:
    """Run all checks, print a table, return process exit code (0 = all ok)."""
    console = Console()
    console.print(
        f"[bold {PALETTE['cyan_400']}]{GLYPH} Milyonus doctor[/] "
        f"[dim]v{__version__} · {platform.system()} {platform.machine()}[/]"
    )

    checks = [
        _python_check(),
        _layout_check(),
        _config_check(),
        _provider_check(),
    ]

    table = Table(show_header=True, header_style=f"bold {PALETTE['chrome_200']}")
    table.add_column("Kontrol")
    table.add_column("Durum")
    table.add_column("Ayrıntı", overflow="fold")
    for c in checks:
        badge = f"[{PALETTE['ok']}]● tamam[/]" if c.ok else f"[{PALETTE['risk']}]● sorun[/]"
        table.add_row(c.name, badge, c.detail)
    console.print(table)

    failed = [c for c in checks if not c.ok]
    if failed:
        console.print(
            f"[{PALETTE['warn']}]{len(failed)} kontrol dikkat gerektiriyor.[/] "
            "Provider anahtarı için `milyonus setup` çalıştırın."
        )
        return 1
    console.print(f"[{PALETTE['ok']}]Her şey yolunda.[/]")
    return 0
