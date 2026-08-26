"""Gateway server — shares the one agent core with every messaging channel.

Responsibilities (PLAN §7):
  - Authorization: default-deny; a user must be paired (or operator-allowlisted)
    before the agent will act. Pairing is driven in-chat with `/pair <code>`.
  - Per-user sessions: each channel+user gets its own conversation history and
    memory session; group messages are marked lower trust.
  - In-chat approval: dangerous tool calls route through the adapter's
    ask_approval, honoring the same RiskEngine as the CLI.

The server is adapter-agnostic; it is handed one or more ChannelAdapters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from milyonus.config.schema import MilyonusConfig
from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.gateway.adapter import (
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
)
from milyonus.gateway.pairing import PairingManager
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.render import build_snapshot
from milyonus.memory.store import MemoryStore
from milyonus.memory.tool import make_memory_tools
from milyonus.prompt.builder import build_system_prompt
from milyonus.providers.base import Message, ProviderError, ToolCall
from milyonus.providers.router import build_provider
from milyonus.security.risk import RiskEngine
from milyonus.tools.fs.tools import make_fs_tools
from milyonus.tools.registry import ToolRegistry
from milyonus.tools.terminal.tools import make_shell_tool
from milyonus.tools.web.tools import make_web_tools

_log = logging.getLogger("milyonus.gateway")


@dataclass
class _UserSession:
    history: list[Message] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)


class GatewayServer:
    def __init__(
        self,
        config: MilyonusConfig,
        adapters: list[ChannelAdapter],
        *,
        workspace,
        pairing: PairingManager | None = None,
        mem_store: MemoryStore | None = None,
    ) -> None:
        self.config = config
        self.adapters = {a.name: a for a in adapters}
        self.workspace = workspace
        self.pairing = pairing or PairingManager()
        self.mem_store = mem_store or MemoryStore()
        self.provider = build_provider(config.provider)
        self.risk = RiskEngine()
        self._sessions: dict[str, _UserSession] = {}

    def _authorized(self, msg: InboundMessage) -> bool:
        if self.config.security.gateway_allow_all_users:
            return True
        return self.pairing.is_paired(msg.channel, msg.user_id)

    def _session_key(self, msg: InboundMessage) -> str:
        return f"{msg.channel}:{msg.user_id}"

    def _get_session(self, msg: InboundMessage) -> _UserSession:
        return self._sessions.setdefault(self._session_key(msg), _UserSession())

    def _build_loop(self, adapter: ChannelAdapter, msg: InboundMessage) -> AgentLoop:
        pipeline = MemoryPipeline(self.mem_store, config=self.config.memory)
        # Group content is lower trust; memory proposals from groups are T3.
        default_source = "third-party" if msg.is_group else "agent-observed"
        mem_tools = make_memory_tools(
            pipeline,
            session_id=self._session_key(msg),
            user_ref=msg.user_id,
            default_source=default_source,
        )
        reg = ToolRegistry()
        for t in make_fs_tools(self.workspace):
            reg.register(t)
        reg.register(make_shell_tool(self.workspace))
        for t in make_web_tools():
            reg.register(t)
        for t in mem_tools:
            reg.register(t)

        snapshot = build_snapshot(self.mem_store, config=self.config.memory)
        system = build_system_prompt(memory=snapshot)

        async def approve(call: ToolCall, risk: str) -> bool:
            decision, reason, findings = self.risk.classify(call, risk)
            if decision == "auto":
                return True
            if decision == "block":
                await adapter.send(OutboundMessage(msg.user_id, f"✗ engellendi: {reason}"))
                return False
            return await adapter.ask_approval(
                msg.user_id, f"⚠ onay: {call.name} {call.arguments} ({reason})"
            )

        session = self._get_session(msg)
        return AgentLoop(
            provider=self.provider,
            tools=reg,
            system_prompt=system,
            budget=session.budget,
            approve=approve,
            max_output_tokens=self.config.provider.max_output_tokens,
        )

    async def handle(self, adapter: ChannelAdapter, msg: InboundMessage) -> None:
        _log.info(
            "inbound %s:%s%s: %s",
            msg.channel,
            msg.user_id,
            " (group)" if msg.is_group else "",
            msg.text[:80],
        )
        # Pairing flow works even before authorization.
        if msg.text.strip().lower().startswith("/pair"):
            await self._handle_pair(adapter, msg)
            return
        if not self._authorized(msg):
            await adapter.send(
                OutboundMessage(
                    msg.user_id,
                    "Bu botu kullanmak için eşleştirme gerekli. "
                    "Operatörden bir kod alıp `/pair <kod>` gönderin.",
                )
            )
            return

        session = self._get_session(msg)
        session.history.append(Message(role="user", content=msg.text))
        try:
            loop = self._build_loop(adapter, msg)
            answer = await loop.run_turn(session.history)
        except ProviderError as exc:
            answer = f"Sağlayıcı hatası: {exc}"
        _log.info("reply -> %s: %s", msg.user_id, (answer or "")[:80])
        await adapter.send(OutboundMessage(msg.user_id, answer or "(boş yanıt)"))

    async def _handle_pair(self, adapter: ChannelAdapter, msg: InboundMessage) -> None:
        parts = msg.text.strip().split()
        if len(parts) < 2:
            await adapter.send(OutboundMessage(msg.user_id, "Kullanım: /pair <kod>"))
            return
        if not self.pairing.can_request(msg.channel, msg.user_id):
            await adapter.send(OutboundMessage(msg.user_id, "Çok sık deneme. Biraz bekleyin."))
            return
        self.pairing.mark_request(msg.channel, msg.user_id)
        ok, message = self.pairing.redeem(msg.channel, msg.user_id, parts[1])
        _log.info("pair attempt %s:%s -> %s", msg.channel, msg.user_id, ok)
        await adapter.send(OutboundMessage(msg.user_id, message))

    async def run(self) -> None:
        import asyncio

        async def bind(adapter: ChannelAdapter) -> None:
            async def handler(m: InboundMessage) -> None:
                await self.handle(adapter, m)

            await adapter.start(handler)

        await asyncio.gather(*(bind(a) for a in self.adapters.values()))
