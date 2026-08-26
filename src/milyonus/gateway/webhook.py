"""Reusable minimal asyncio webhook server for push-based channels.

WhatsApp and Slack both receive inbound events via HTTP POST (and a GET or
challenge handshake). This is a dependency-free HTTP/1.1 server that parses a
single request per connection and hands the method, path, query, headers, and
raw body to a callback. Kept intentionally small — it exists so channel adapters
don't each reimplement socket plumbing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlparse

# (status, body) the handler returns for a request.
Response = tuple[int, str]


@dataclass(slots=True)
class Request:
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: bytes


Handler = Callable[[Request], Awaitable[Response]]


class WebhookServer:
    def __init__(self, handler: Handler, *, host: str = "0.0.0.0", port: int = 8080):
        self.handler = handler
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def _handle_conn(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                return
            method, target, _ = request_line.decode("latin1").split(" ", 2)
            headers: dict[str, str] = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                k, _, v = line.decode("latin1").partition(":")
                headers[k.strip().lower()] = v.strip()
            length = int(headers.get("content-length", "0"))
            body = await reader.readexactly(length) if length else b""
            parsed = urlparse(target)
            req = Request(method, parsed.path, parsed.query, headers, body)
            status, out = await self.handler(req)
            await self._respond(writer, status, out)
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

    async def serve(self) -> None:
        self._server = await asyncio.start_server(self._handle_conn, self.host, self.port)
        async with self._server:
            await self._server.serve_forever()
