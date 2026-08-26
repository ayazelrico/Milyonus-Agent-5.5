"""Slack adapter (P2) — Events API over a webhook (reuses WebhookServer).

Slack pushes events to a request URL. This adapter:
  - Answers the one-time url_verification challenge.
  - Verifies Slack's signature (v0=HMAC-SHA256 over "v0:timestamp:body") when a
    signing secret is set — mandatory in that case, with a 5-minute timestamp
    window to stop replay.
  - Handles message events, replying via chat.postMessage.

Credentials from the environment:
  SLACK_BOT_TOKEN       — xoxb- token for chat.postMessage
  SLACK_SIGNING_SECRET  — for request signature verification (recommended)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

import httpx

from milyonus.gateway.adapter import (
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)
from milyonus.gateway.webhook import Request, WebhookServer

_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
_YES = {"e", "evet", "y", "yes", "ok", "tamam", "olur", "onayla"}


class SlackAdapter:
    def __init__(
        self,
        *,
        bot_token: str | None = None,
        signing_secret: str | None = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self.name = "slack"
        self._token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self._secret = signing_secret or os.environ.get("SLACK_SIGNING_SECRET", "")
        self.host = host
        self.port = port
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        import asyncio

        self._queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._approval_waiters: dict[str, asyncio.Future[str]] = {}
        self._seen_events: set[str] = set()

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            _POST_MESSAGE,
            headers={"Authorization": f"Bearer {self._token}"},
            json={"channel": message.user_id, "text": message.text or "(empty)"},
        )

    async def ask_approval(self, user_id: str, prompt: str) -> bool:
        import asyncio

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

    # --- signature (pure) ----------------------------------------------

    def verify_signature(self, headers: dict[str, str], body: bytes) -> bool:
        if not self._secret:
            return True
        ts = headers.get("x-slack-request-timestamp", "")
        sig = headers.get("x-slack-signature", "")
        if not ts or not sig:
            return False
        # Reject requests older than 5 minutes (replay protection).
        try:
            if abs(time.time() - int(ts)) > 300:
                return False
        except ValueError:
            return False
        base = f"v0:{ts}:{body.decode('utf-8', 'replace')}".encode()
        expected = "v0=" + hmac.new(self._secret.encode(), base, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def parse_event(self, payload: dict) -> InboundMessage | None:
        event = payload.get("event", {})
        # Ignore bot messages / non-text / edits to avoid loops.
        if event.get("type") != "message" or event.get("bot_id") or "subtype" in event:
            return None
        text = event.get("text", "")
        channel = event.get("channel", "")
        if not text or not channel:
            return None
        return InboundMessage(
            channel="slack",
            user_id=channel,  # reply into the same channel/DM
            text=text,
            display_name=event.get("user", ""),
            is_group=event.get("channel_type") in ("channel", "group"),
        )

    async def _on_request(self, req: Request) -> tuple[int, str]:
        if req.method != "POST":
            return (405, "method not allowed")
        if not self.verify_signature(req.headers, req.body):
            return (401, "bad signature")
        try:
            payload = json.loads(req.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return (400, "bad json")
        # URL verification handshake.
        if payload.get("type") == "url_verification":
            return (200, payload.get("challenge", ""))
        # Deduplicate Slack retries by event_id.
        event_id = payload.get("event_id")
        if event_id and event_id in self._seen_events:
            return (200, "dup")
        if event_id:
            self._seen_events.add(event_id)
        msg = self.parse_event(payload)
        if msg is not None:
            await self._queue.put(msg)
        return (200, "ok")

    async def _dispatch(self, handler: MessageHandler) -> None:
        while True:
            msg = await self._queue.get()
            waiter = self._approval_waiters.get(msg.user_id)
            if waiter is not None and not waiter.done():
                waiter.set_result(msg.text)
                continue
            await handler(msg)

    async def start(self, handler: MessageHandler) -> None:
        import asyncio

        if not self._token:
            raise RuntimeError("SLACK_BOT_TOKEN must be set.")
        asyncio.create_task(self._dispatch(handler))
        server = WebhookServer(self._on_request, host=self.host, port=self.port)
        await server.serve()

    async def close(self) -> None:
        await self._client.aclose()
