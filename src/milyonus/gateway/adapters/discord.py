"""Discord adapter (P2) — Gateway WebSocket + REST for sending.

Discord has no long-polling: a bot connects to the Gateway over a WebSocket,
identifies, heartbeats, and receives MESSAGE_CREATE events. Sending uses the REST
API. This needs the optional `websockets` dependency (`pip install
milyonus-agent[discord]`).

The message-parsing and payload logic is separated from the socket so it can be
unit-tested without a live connection. Credentials from the environment:
  DISCORD_BOT_TOKEN — the bot token (needs the MESSAGE CONTENT intent enabled)
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx

from milyonus.gateway.adapter import (
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)

_API = "https://discord.com/api/v10"
_GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"
# Intents: GUILD_MESSAGES (1<<9) | DIRECT_MESSAGES (1<<12) | MESSAGE_CONTENT (1<<15).
_INTENTS = (1 << 9) | (1 << 12) | (1 << 15)
_YES = {"e", "evet", "y", "yes", "ok", "tamam", "olur", "onayla"}


class DiscordAdapter:
    def __init__(self, *, token: str | None = None) -> None:
        self.name = "discord"
        self._token = token or os.environ.get("DISCORD_BOT_TOKEN", "")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._session_id: str | None = None
        self._seq: int | None = None
        self._bot_user_id: str | None = None
        self._approval_waiters: dict[str, asyncio.Future[str]] = {}

    async def send(self, message: OutboundMessage) -> None:
        text = message.text or "(empty)"
        for i in range(0, len(text), 1900):
            await self._client.post(
                f"{_API}/channels/{message.user_id}/messages",
                headers={"Authorization": f"Bot {self._token}"},
                json={"content": text[i : i + 1900]},
            )

    async def ask_approval(self, user_id: str, prompt: str) -> bool:
        await self.send(OutboundMessage(user_id, f"{prompt}\nReply: yes / no"))
        fut: asyncio.Future[str] = asyncio.get_event_loop().create_future()
        self._approval_waiters[user_id] = fut
        try:
            answer = await asyncio.wait_for(fut, timeout=300.0)
        except TimeoutError:
            return False
        finally:
            self._approval_waiters.pop(user_id, None)
        return answer.strip().lower() in _YES

    # --- pure parsing (unit-testable) ----------------------------------

    def parse_message_create(self, data: dict) -> InboundMessage | None:
        """Turn a MESSAGE_CREATE payload into an InboundMessage, ignoring the
        bot's own messages and empty content."""
        author = data.get("author", {})
        if author.get("bot") or author.get("id") == self._bot_user_id:
            return None
        content = data.get("content", "")
        channel_id = data.get("channel_id", "")
        if not content or not channel_id:
            return None
        return InboundMessage(
            channel="discord",
            user_id=channel_id,  # reply into the same channel
            text=content,
            display_name=author.get("username", ""),
            is_group="guild_id" in data,  # guild messages are group-like
        )

    def _identify_payload(self) -> dict:
        return {
            "op": 2,
            "d": {
                "token": self._token,
                "intents": _INTENTS,
                "properties": {"os": "linux", "browser": "milyonus", "device": "milyonus"},
            },
        }

    # --- gateway loop ---------------------------------------------------

    async def start(self, handler: MessageHandler) -> None:
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "Discord requires 'websockets': pip install milyonus-agent[discord]"
            ) from exc
        if not self._token:
            raise RuntimeError("DISCORD_BOT_TOKEN must be set.")

        async with websockets.connect(_GATEWAY, max_size=None) as ws:
            hello = json.loads(await ws.recv())
            interval = hello["d"]["heartbeat_interval"] / 1000.0
            await ws.send(json.dumps(self._identify_payload()))

            async def heartbeat() -> None:
                while True:
                    await asyncio.sleep(interval)
                    await ws.send(json.dumps({"op": 1, "d": self._seq}))

            hb_task = asyncio.create_task(heartbeat())
            try:
                async for raw in ws:
                    event = json.loads(raw)
                    if event.get("s") is not None:
                        self._seq = event["s"]
                    if event.get("op") != 0:
                        continue
                    t = event.get("t")
                    if t == "READY":
                        self._session_id = event["d"].get("session_id")
                        self._bot_user_id = event["d"].get("user", {}).get("id")
                    elif t == "MESSAGE_CREATE":
                        msg = self.parse_message_create(event["d"])
                        if msg is None:
                            continue
                        waiter = self._approval_waiters.get(msg.user_id)
                        if waiter is not None and not waiter.done():
                            waiter.set_result(msg.text)
                            continue
                        await handler(msg)
            finally:
                hb_task.cancel()

    async def close(self) -> None:
        await self._client.aclose()
