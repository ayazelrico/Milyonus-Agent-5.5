"""Load and validate Milyonus config from disk.

The loader is strict (ADR-009): a malformed or unknown key raises ConfigError at
startup rather than silently degrading. A missing config file is fine — defaults
apply — because a first run should just work.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from milyonus.config.paths import config_file
from milyonus.config.schema import MilyonusConfig


class ConfigError(Exception):
    """Raised when the config file exists but is invalid."""


def load_config(path: Path | None = None) -> MilyonusConfig:
    """Return the validated config, applying defaults when the file is absent."""
    path = path or config_file()
    if not path.exists():
        return MilyonusConfig()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: TOML söz dizimi hatası: {exc}") from exc
    try:
        return MilyonusConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path}: geçersiz yapılandırma:\n{exc}") from exc
