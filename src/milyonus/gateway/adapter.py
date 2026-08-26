"""Channel adapter interface — one thin adapter per messaging channel.

Every channel (Telegram, WhatsApp, Discord, …) implements this so the gateway
server can drive them all with one code path (PLAN §7). The adapter's job is
narrow: receive inbound messages, send outbound text, and ask a yes/no approval
question in-chat. Everything else — the agent loop, memory, security — is shared.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class InboundMessage:
    channel: str
    user_id: str  # external id (telegram chat id, etc.)
    text: str
    display_name: str = ""
    is_group: bool = False  # group messages default to lower trust (PLAN §7)


@dataclass(slots=True)
class OutboundMessage:
    user_id: str
    text: str


# Handler the server registers; the adapter calls it per inbound message.
MessageHandler = Callable[[InboundMessage], Awaitable[None]]


@runtime_checkable
class ChannelAdapter(Protocol):
    name: str

    async def start(self, handler: MessageHandler) -> None:
        """Begin receiving messages, dispatching each to `handler`. Runs until
        cancelled."""
        ...

    async def send(self, message: OutboundMessage) -> None:
        """Send text to a user."""
        ...

    async def ask_approval(self, user_id: str, prompt: str) -> bool:
        """Ask a yes/no question in-chat and await the answer."""
        ...

    def incoming(self) -> AsyncIterator[InboundMessage]:  # pragma: no cover
        """Optional: expose a stream of inbound messages (used by tests)."""
        ...
