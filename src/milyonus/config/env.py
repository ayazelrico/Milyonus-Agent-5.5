"""Load secrets from ~/.milyonus/.env into the process environment.

Keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, …) live in ~/.milyonus/.env with mode
0600, never in config.toml and never in the repo. This loader is called once at
startup. It does not override variables already set in the real environment, so
an explicit `export` or CI secret always wins over the file.
"""

from __future__ import annotations

import os
import stat

from milyonus.config.paths import env_file

# Env var names we consider secret — warned about if the .env file is world-readable.
_SECRET_HINT = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH")


def _parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def load_env() -> list[str]:
    """Load ~/.milyonus/.env. Return the names of keys applied (never values)."""
    path = env_file()
    if not path.exists():
        return []
    applied: list[str] = []
    for key, value in _parse(path.read_text(encoding="utf-8")).items():
        if key not in os.environ:  # real environment wins
            os.environ[key] = value
            applied.append(key)
    return applied


def env_file_is_private() -> bool | None:
    """Return True if ~/.milyonus/.env is 0600-ish, False if lax, None if absent."""
    path = env_file()
    if not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    # Fail if group/other have any access.
    return (mode & 0o077) == 0
