"""Minimal MCP (Model Context Protocol) stdio client (PLAN §3.4, §6 layer 4).

Connects to an MCP server subprocess over stdio/JSON-RPC, lists its tools, and
exposes them as Milyonus Tools. The subprocess is spawned with a filtered
environment (safe_env) so API keys never leak into third-party servers, and tool
output is redacted. Kept intentionally small: initialize, tools/list, tools/call.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from milyonus.security.redact import redact, safe_env
from milyonus.tools.registry import Tool

_PROTOCOL_VERSION = "2024-11-05"


class MCPClient:
    def __init__(self, command: list[str], *, env_passthrough: list[str] | None = None):
        self.command = command
        self.env_passthrough = env_passthrough or []
        self._proc: asyncio.subprocess.Process | None = None
        self._next_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=safe_env(dict(os.environ), extra_allow=self.env_passthrough),
        )
        await self._request(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "milyonus", "version": "5.5.0"},
            },
        )
        await self._notify("notifications/initialized", {})

    async def _send(self, payload: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()

    async def _notify(self, method: str, params: dict) -> None:
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _request(self, method: str, params: dict) -> dict:
        async with self._lock:
            self._next_id += 1
            rid = self._next_id
            await self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            assert self._proc and self._proc.stdout
            while True:
                line = await self._proc.stdout.readline()
                if not line:
                    raise RuntimeError("MCP sunucusu beklenmedik şekilde kapandı")
                msg = json.loads(line.decode("utf-8"))
                if msg.get("id") == rid:
                    if "error" in msg:
                        raise RuntimeError(redact(str(msg["error"])))
                    return msg.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> str:
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        # MCP returns content blocks; join text and redact.
        blocks = result.get("content", [])
        text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return redact(text or json.dumps(result, ensure_ascii=False))

    async def as_tools(self, *, prefix: str = "mcp") -> list[Tool]:
        """Wrap the server's tools as Milyonus Tools (namespaced by prefix)."""
        tools: list[Tool] = []
        for spec in await self.list_tools():
            name = spec["name"]

            async def handler(args: dict, _name=name) -> str:
                return await self.call_tool(_name, args)

            tools.append(
                Tool(
                    name=f"{prefix}_{name}",
                    description=spec.get("description", name),
                    parameters=spec.get("inputSchema", {"type": "object"}),
                    handler=handler,
                    risk="caution",  # external servers are caution by default
                )
            )
        return tools

    async def close(self) -> None:
        if self._proc:
            self._proc.terminate()
            await self._proc.wait()
