"""Telegram adapter (P0) — Bot API over long-polling, on httpx (no extra deps).

Receives updates via getUpdates, sends via sendMessage. In-chat approval is
handled by sending the question and waiting for the next message from that user
to be "yes/no". The bot token comes from TELEGRAM_BOT_TOKEN (never config).
"""

from __future__ import annotations

import asyncio
import os

import httpx

from milyonus.gateway.adapter import (
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)

_API = "https://api.telegram.org"
_YES = {"e", "evet", "y", "yes", "ok", "tamam", "olur"}


class TelegramAdapter:
    def __init__(self, *, token: str | None = None) -> None:
        self.name = "telegram"
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._offset = 0
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(65.0))
        # Pending approval waiters: user_id -> Future[str] for the next message.
        self._approval_waiters: dict[str, asyncio.Future[str]] = {}

    def _url(self, method: str) -> str:
        return f"{_API}/bot{self._token}/{method}"

    async def send(self, message: OutboundMessage) -> None:
        # Telegram caps messages at 4096 chars; chunk long answers.
        text = message.text or "(boş)"
        for i in range(0, len(text), 4000):
            await self._client.post(
                self._url("sendMessage"),
                json={"chat_id": message.user_id, "text": text[i : i + 4000]},
            )

    async def ask_approval(self, user_id: str, prompt: str) -> bool:
        await self.send(OutboundMessage(user_id, f"{prompt}\nCevap: evet / hayır"))
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[str] = loop.create_future()
        self._approval_waiters[user_id] = fut
        try:
            answer = await asyncio.wait_for(fut, timeout=300.0)
        except TimeoutError:
            return False
        finally:
            self._approval_waiters.pop(user_id, None)
        return answer.strip().lower() in _YES

    async def start(self, handler: MessageHandler) -> None:
        if not self._token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN ayarlı değil.")
        while True:
            try:
                resp = await self._client.get(
                    self._url("getUpdates"),
                    params={"offset": self._offset, "timeout": 60},
                )
                data = resp.json()
            except (httpx.HTTPError, ValueError):
                await asyncio.sleep(3)
                continue
            for update in data.get("result", []):
                self._offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg or "text" not in msg:
                    continue
                chat = msg["chat"]
                user_id = str(chat["id"])
                text = msg["text"]
                # If this user has a pending approval, feed the answer to it.
                waiter = self._approval_waiters.get(user_id)
                if waiter is not None and not waiter.done():
                    waiter.set_result(text)
                    continue
                inbound = InboundMessage(
                    channel="telegram",
                    user_id=user_id,
                    text=text,
                    display_name=chat.get("first_name", ""),
                    is_group=chat.get("type") in ("group", "supergroup"),
                )
                await handler(inbound)

    async def close(self) -> None:
        await self._client.aclose()
