"""Filesystem tools: read, write, list. Confined to a working root.

Every path is resolved and checked to stay within the session's working root, so
the agent cannot read or write outside it without an explicit operator setting.
Write is classified "caution": it is reversible via the selfmod snapshot but still
changes the disk, so the loop may surface it depending on policy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from milyonus.tools.registry import Tool

_MAX_READ = 200_000  # bytes; guards against dumping a huge file into context


class PathEscape(Exception):
    """Raised when a requested path resolves outside the working root."""


def _resolve(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    root_r = root.resolve()
    if p != root_r and root_r not in p.parents:
        raise PathEscape(f"Path outside the working root: {rel}")
    return p


def make_fs_tools(root: Path) -> list[Tool]:
    root = root.resolve()

    async def read_file(args: dict[str, Any]) -> str:
        p = _resolve(root, args["path"])
        if not p.exists():
            return f"Dosya yok: {args['path']}"
        data = p.read_bytes()[:_MAX_READ]
        text = data.decode("utf-8", "replace")
        suffix = "\n…(kesildi)" if p.stat().st_size > _MAX_READ else ""
        return text + suffix

    async def write_file(args: dict[str, Any]) -> str:
        p = _resolve(root, args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        content = args["content"]
        p.write_text(content, encoding="utf-8")
        return f"Wrote: {args['path']} ({len(content)} chars)"

    async def list_dir(args: dict[str, Any]) -> str:
        p = _resolve(root, args.get("path", "."))
        if not p.is_dir():
            return f"Not a directory: {args.get('path', '.')}"
        entries = sorted(f"{'d' if e.is_dir() else 'f'} {e.name}" for e in p.iterdir())
        return "\n".join(entries) if entries else "(empty)"

    return [
        Tool(
            name="read_file",
            description="Read the contents of a file within the working root.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path"}},
                "required": ["path"],
            },
            handler=read_file,
            risk="safe",
        ),
        Tool(
            name="write_file",
            description="Write content to a file (overwrites if it exists).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=write_file,
            risk="caution",
        ),
        Tool(
            name="list_dir",
            description="List the contents of a directory.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path"}},
            },
            handler=list_dir,
            risk="safe",
        ),
    ]
