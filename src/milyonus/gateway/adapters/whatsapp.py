"""WhatsApp adapter (P1) — official Cloud API over a webhook (PLAN §7, F5.5).

Unlike Telegram (long-polling, the agent pulls), the WhatsApp Cloud API *pushes*
inbound messages to a webhook, so this adapter runs a small HTTP server:

  GET  /webhook  — Meta's verification handshake (echoes hub.challenge).
  POST /webhook  — inbound messages; optionally HMAC-verified against the app
                   secret (X-Hub-Signature-256) before they are trusted.

Outbound goes to graph.facebook.com. Inbound is enqueued and processed by a
worker so the HTTP response returns immediately (Meta retries slow webhooks).
In-chat approval reuses the next-message mechanism, like Telegram.

Credentials come from the environment, never config:
  WHATSAPP_TOKEN            — Graph API access token
  WHATSAPP_PHONE_NUMBER_ID  — sender phone number id
  WHATSAPP_VERIFY_TOKEN     — shared secret for the GET handshake
  WHATSAPP_APP_SECRET       — optional; enables POST signature verification

The unofficial whatsapp-web.js/Baileys bridge is intentionally NOT shipped: it
risks account bans (PLAN §7). See docs for how to run it yourself if you accept
that risk.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qs, urlparse

import httpx

from milyonus.gateway.adapter import (
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)

_GRAPH = "https://graph.facebook.com/v21.0"
_YES = {"e", "evet", "y", "yes", "ok", "tamam", "olur", "onayla"}


class WhatsAppCloudAdapter:
    def __init__(
        self,
        *,
        token: str | None = None,
        phone_number_id: str | None = None,
        verify_token: str | None = None,
        app_secret: str | None = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self.name = "whatsapp"
        self._token = token or os.environ.get("WHATSAPP_TOKEN", "")
        self._phone_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self._verify_token = verify_token or os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
        self._app_secret = app_secret or os.environ.get("WHATSAPP_APP_SECRET", "")
        self.host = host
        self.port = port
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._approval_waiters: dict[str, asyncio.Future[str]] = {}

    # --- outbound -------------------------------------------------------

    async def send(self, message: OutboundMessage) -> None:
        text = message.text or "(boş)"
        for i in range(0, len(text), 4000):
            await self._client.post(
                f"{_GRAPH}/{self._phone_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": message.user_id,
                    "type": "text",
                    "text": {"body": text[i : i + 4000]},
                },
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

    # --- webhook parsing (pure, unit-testable) --------------------------

    def verify_signature(self, raw_body: bytes, signature_header: str | None) -> bool:
        """Verify X-Hub-Signature-256. If no app secret is configured, skip
        (returns True) — but a configured secret makes it mandatory."""
        if not self._app_secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(self._app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header[len("sha256=") :])

    @staticmethod
    def parse_inbound(payload: dict) -> list[InboundMessage]:
        """Extract InboundMessages from a Cloud API webhook payload."""
        out: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = {
                    c["wa_id"]: c.get("profile", {}).get("name", "")
                    for c in value.get("contacts", [])
                }
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue
                    wa_id = msg["from"]
                    out.append(
                        InboundMessage(
                            channel="whatsapp",
                            user_id=wa_id,
                            text=msg["text"]["body"],
                            display_name=contacts.get(wa_id, ""),
                            is_group=False,  # Cloud API DMs; groups need extra setup
                        )
                    )
        return out

    def handle_verification(self, query: str) -> tuple[int, str]:
        """Handle the GET handshake. Returns (status, body)."""
        params = parse_qs(query)
        mode = params.get("hub.mode", [""])[0]
        token = params.get("hub.verify_token", [""])[0]
        challenge = params.get("hub.challenge", [""])[0]
        if mode == "subscribe" and token == self._verify_token:
            return (200, challenge)
        return (403, "forbidden")

    # --- HTTP server ----------------------------------------------------

    async def _dispatch_inbound(self, handler: MessageHandler) -> None:
        while True:
            msg = await self._queue.get()
            waiter = self._approval_waiters.get(msg.user_id)
            if waiter is not None and not waiter.done():
                waiter.set_result(msg.text)
                continue
            await handler(msg)

    async def _handle_conn(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return
            method, target, _ = request_line.decode("latin1").split(" ", 2)
            headers: dict[str, str] = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                k, _, v = line.decode("latin1").partition(":")
                headers[k.strip().lower()] = v.strip()

            if method == "GET":
                status, body = self.handle_verification(urlparse(target).query)
                await self._respond(writer, status, body)
                return

            if method == "POST":
                length = int(headers.get("content-length", "0"))
                raw = await reader.readexactly(length) if length else b""
                sig = headers.get("x-hub-signature-256")
                if not self.verify_signature(raw, sig):
                    await self._respond(writer, 401, "bad signature")
                    return
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    await self._respond(writer, 400, "bad json")
                    return
                for msg in self.parse_inbound(payload):
                    await self._queue.put(msg)
                await self._respond(writer, 200, "EVENT_RECEIVED")
                return

            await self._respond(writer, 405, "method not allowed")
        except (asyncio.IncompleteReadError, ConnectionError, ValueError):
            pass
        finally:
            writer.close()

    @staticmethod
    async def _respond(writer: asyncio.StreamWriter, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        head = (
            f"HTTP/1.1 {status} OK\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("latin1")
        writer.write(head + payload)
        await writer.drain()

    async def start(self, handler: MessageHandler) -> None:
        if not self._token or not self._phone_id:
            raise RuntimeError("WHATSAPP_TOKEN ve WHATSAPP_PHONE_NUMBER_ID ayarlı olmalı.")
        asyncio.create_task(self._dispatch_inbound(handler))
        server = await asyncio.start_server(self._handle_conn, self.host, self.port)
        async with server:
            await server.serve_forever()

    async def close(self) -> None:
        await self._client.aclose()
