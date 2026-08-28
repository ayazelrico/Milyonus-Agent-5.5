"""MCP server manager — connect configured servers and surface their tools.

Reads `config.mcp_servers`, spawns each enabled server as a stdio subprocess,
lists its tools, and namespaces them as `mcp_<server>_<tool>` so several servers
coexist without collisions. The manager is deliberately fault-tolerant: a server
that fails to start (bad command, crash, timeout) is recorded in `errors` and
skipped — one broken third-party server can never take down the agent or the
other servers.

Lifecycle: `await start()` once at session start, use `tools()` to register,
`await close()` on exit. Servers are untrusted subprocesses (filtered env,
redacted output, RiskEngine-gated tools) — see MCPClient.
"""

from __future__ import annotations

import asyncio
import logging

from milyonus.config.schema import MCPServerConfig
from milyonus.tools.mcp.client import MCPClient
from milyonus.tools.registry import Tool

_log = logging.getLogger("milyonus.mcp")

# A server that hangs on initialize must not stall startup forever.
_START_TIMEOUT = 20.0


class MCPManager:
    def __init__(self, servers: list[MCPServerConfig]) -> None:
        self.servers = servers
        self._clients: list[MCPClient] = []
        self._tools: list[Tool] = []
        # server name -> error string (why it did not connect / expose tools).
        self.errors: dict[str, str] = {}
        # server name -> list of tool names it contributed (after namespacing).
        self.connected: dict[str, list[str]] = {}

    async def start(self) -> None:
        """Connect every enabled server, gathering tools. Failures are recorded,
        never raised."""
        for cfg in self.servers:
            if not cfg.enabled:
                continue
            try:
                client = MCPClient(cfg.command, env_passthrough=cfg.env_passthrough)
                await asyncio.wait_for(client.start(), timeout=_START_TIMEOUT)
                tools = await asyncio.wait_for(
                    client.as_tools(prefix=f"mcp_{cfg.name}", risk=cfg.risk),
                    timeout=_START_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001 - isolate a bad server
                self.errors[cfg.name] = f"{type(exc).__name__}: {exc}"
                _log.warning("MCP server %r failed to connect: %s", cfg.name, exc)
                continue
            self._clients.append(client)
            self._tools.extend(tools)
            self.connected[cfg.name] = [t.name for t in tools]
            _log.info("MCP server %r connected: %d tools", cfg.name, len(tools))

    def tools(self) -> list[Tool]:
        return list(self._tools)

    def register_into(self, registry) -> int:
        """Register gathered tools into a ToolRegistry, skipping name collisions
        (a duplicate must not crash the surface). Returns the count registered."""
        n = 0
        for tool in self._tools:
            if registry.get(tool.name) is not None:
                _log.warning("MCP tool %r shadowed by an existing tool — skipped", tool.name)
                continue
            registry.register(tool)
            n += 1
        return n

    async def close(self) -> None:
        import contextlib

        for client in self._clients:
            with contextlib.suppress(Exception):  # best-effort teardown
                await client.close()
        self._clients.clear()
