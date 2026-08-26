"""ACP (Agent Client Protocol) server — editor-native integration (PLAN §3.7).

Exposes Milyonus as an agent an ACP client (e.g. Zed) drives over stdio with
newline-delimited JSON-RPC. The editor is the client; Milyonus is the agent. We
implement the core subset:

  initialize       — negotiate protocol version + advertise capabilities
  session/new      — create a session bound to a working directory
  session/prompt   — run a turn, streaming `session/update` notifications with
                     assistant text chunks, then return a stopReason
  session/cancel   — best-effort cancel

The transport is injectable (an asyncio reader/writer pair) so the protocol can
be tested without real pipes. The same agent core (provider, tools, loop, memory)
backs it — ACP is just another surface.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from milyonus.config.schema import MilyonusConfig
from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.render import build_snapshot
from milyonus.memory.store import MemoryStore
from milyonus.memory.tool import make_memory_tools
from milyonus.prompt.builder import build_system_prompt
from milyonus.providers.base import Message, Provider, ProviderError, ToolCall
from milyonus.providers.router import build_provider
from milyonus.tools.fs.tools import make_fs_tools
from milyonus.tools.registry import ToolRegistry
from milyonus.tools.terminal.tools import make_shell_tool
from milyonus.tools.web.tools import make_web_tools

_PROTOCOL_VERSION = 1


@dataclass
class _Session:
    id: str
    cwd: Path
    history: list[Message] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)


class ACPServer:
    def __init__(
        self,
        config: MilyonusConfig,
        *,
        provider: Provider | None = None,
        mem_store: MemoryStore | None = None,
    ) -> None:
        self.config = config
        self.provider = provider or build_provider(config.provider)
        self.mem_store = mem_store or MemoryStore()
        self._sessions: dict[str, _Session] = {}
        self._writer: asyncio.StreamWriter | None = None

    # --- transport ------------------------------------------------------

    async def serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Read newline-delimited JSON-RPC until EOF, dispatching each message."""
        self._writer = writer
        while True:
            line = await reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            response = await self._dispatch(msg)
            if response is not None:
                await self._write(response)

    async def _write(self, obj: dict) -> None:
        assert self._writer is not None
        self._writer.write((json.dumps(obj) + "\n").encode("utf-8"))
        await self._writer.drain()

    async def _notify(self, method: str, params: dict) -> None:
        await self._write({"jsonrpc": "2.0", "method": method, "params": params})

    # --- dispatch -------------------------------------------------------

    async def _dispatch(self, msg: dict) -> dict | None:
        method = msg.get("method")
        mid = msg.get("id")
        try:
            if method == "initialize":
                result = self._initialize(msg.get("params", {}))
            elif method == "session/new":
                result = self._session_new(msg.get("params", {}))
            elif method == "session/prompt":
                result = await self._session_prompt(msg.get("params", {}))
            elif method == "session/cancel":
                result = self._session_cancel(msg.get("params", {}))
            else:
                if mid is None:
                    return None  # unknown notification: ignore
                return _error(mid, -32601, f"unknown method: {method}")
        except Exception as exc:  # noqa: BLE001 - surface as JSON-RPC error
            if mid is None:
                return None
            return _error(mid, -32603, str(exc))
        if mid is None:
            return None  # it was a notification
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def _initialize(self, _params: dict) -> dict:
        return {
            "protocolVersion": _PROTOCOL_VERSION,
            "agentCapabilities": {
                "loadSession": False,
                "promptCapabilities": {"image": False, "audio": False},
            },
            "authMethods": [],
        }

    def _session_new(self, params: dict) -> dict:
        cwd = Path(params.get("cwd", ".")).resolve()
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        self._sessions[sid] = _Session(id=sid, cwd=cwd)
        return {"sessionId": sid}

    def _session_cancel(self, params: dict) -> dict:
        # Best-effort: sessions are single-turn here, so nothing to interrupt yet.
        return {}

    def _build_loop(self, session: _Session) -> AgentLoop:
        pipeline = MemoryPipeline(self.mem_store, config=self.config.memory)
        mem_tools = make_memory_tools(pipeline, session_id=session.id, user_ref="editor")
        reg = ToolRegistry()
        for t in make_fs_tools(session.cwd):
            reg.register(t)
        reg.register(make_shell_tool(session.cwd))
        for t in make_web_tools():
            reg.register(t)
        for t in mem_tools:
            reg.register(t)

        snapshot = build_snapshot(self.mem_store, config=self.config.memory)
        system = build_system_prompt(memory=snapshot)

        async def on_text(chunk: str) -> None:
            await self._notify(
                "session/update",
                {
                    "sessionId": session.id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": chunk},
                    },
                },
            )

        async def on_tool(call: ToolCall) -> None:
            await self._notify(
                "session/update",
                {
                    "sessionId": session.id,
                    "update": {
                        "sessionUpdate": "tool_call",
                        "toolCallId": call.id,
                        "title": call.name,
                        "status": "pending",
                    },
                },
            )

        return AgentLoop(
            provider=self.provider,
            tools=reg,
            system_prompt=system,
            budget=session.budget,
            on_text=on_text,
            on_tool=on_tool,
            max_output_tokens=self.config.provider.max_output_tokens,
        )

    async def _session_prompt(self, params: dict) -> dict:
        sid = params.get("sessionId", "")
        session = self._sessions.get(sid)
        if session is None:
            raise ValueError(f"unknown session: {sid}")
        text = _extract_text(params.get("prompt", []))
        session.history.append(Message(role="user", content=text))
        try:
            loop = self._build_loop(session)
            await loop.run_turn(session.history)
            return {"stopReason": "end_turn"}
        except ProviderError as exc:
            await self._notify(
                "session/update",
                {
                    "sessionId": sid,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": f"Provider error: {exc}"},
                    },
                },
            )
            return {"stopReason": "refusal"}


def _extract_text(prompt_blocks: list) -> str:
    parts = [
        b.get("text", "") for b in prompt_blocks if isinstance(b, dict) and b.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p)


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


async def run_stdio(config: MilyonusConfig) -> None:
    """Serve ACP over the process's stdin/stdout."""
    import sys

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    server = ACPServer(config)
    await server.serve(reader, writer)
