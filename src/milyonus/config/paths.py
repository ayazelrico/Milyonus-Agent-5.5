"""Filesystem layout for Milyonus state under ~/.milyonus/.

All runtime state lives under a single data root so a deployment is one directory
to back up, move, or wipe. The root can be overridden with MILYONUS_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """Return the Milyonus data root (~/.milyonus by default)."""
    override = os.environ.get("MILYONUS_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".milyonus"


def config_file() -> Path:
    return data_root() / "config.toml"


def state_db() -> Path:
    return data_root() / "state.db"


def memory_dir() -> Path:
    return data_root() / "memory"


def skills_dir() -> Path:
    return data_root() / "skills"


def logs_dir() -> Path:
    return data_root() / "logs"


def env_file() -> Path:
    return data_root() / ".env"


def ensure_layout() -> Path:
    """Create the data root and standard subdirectories if missing.

    Directories are created with mode 0o700 since they hold credentials and
    verified memory. Returns the data root.
    """
    root = data_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    for sub in (memory_dir(), skills_dir(), logs_dir()):
        sub.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def introduced_marker() -> Path:
    return data_root() / ".introduced"


def is_first_run() -> bool:
    """True until the agent has introduced itself once."""
    return not introduced_marker().exists()


def mark_introduced() -> None:
    m = introduced_marker()
    m.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    m.touch()
