"""Shell tool: run a command in the working root.

Classified "danger": a shell command can do irreversible or outward-reaching
things, so the loop routes it through approval (F4 RiskEngine will refine this;
in F1 the flag is honored by the CLI approval prompt). Output is captured with a
timeout and truncated so a runaway command cannot flood the context.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from milyonus.security.redact import redact, safe_env
from milyonus.tools.registry import Tool

_MAX_OUTPUT = 100_000
_TIMEOUT = 120.0


def make_shell_tool(root: Path) -> Tool:
    root = root.resolve()

    async def run_shell(args: dict[str, Any]) -> str:
        command = args["command"]
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=safe_env(dict(os.environ)),  # strip secrets from the child env
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT)
        except TimeoutError:
            proc.kill()
            return f"(zaman aşımı: {_TIMEOUT:.0f}s sonra öldürüldü)"
        text = redact(out.decode("utf-8", "replace")[:_MAX_OUTPUT])
        return f"[çıkış kodu {proc.returncode}]\n{text}"

    return Tool(
        name="run_shell",
        description="Çalışma kökünde bir kabuk (shell) komutu çalıştırır.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Çalıştırılacak komut"}},
            "required": ["command"],
        },
        handler=run_shell,
        risk="danger",
    )
