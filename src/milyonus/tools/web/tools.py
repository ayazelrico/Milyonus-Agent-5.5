"""Web fetch tool — SSRF-guarded, output-redacted.

Every URL (including each redirect hop) is validated by the SSRF checker before a
request is made, and the response text is redacted of anything secret-shaped
before it returns to the model. Classified "caution": it reaches the network but
is read-only.
"""

from __future__ import annotations

from typing import Any

import httpx

from milyonus.security.redact import redact
from milyonus.security.ssrf import SSRFBlocked, check_url
from milyonus.tools.registry import Tool

_MAX_BYTES = 200_000


def make_web_tools() -> list[Tool]:
    async def web_fetch(args: dict[str, Any]) -> str:
        url = args["url"]
        try:
            check_url(url)
        except SSRFBlocked as exc:
            return f"engellendi (SSRF): {exc}"
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
                # Manual redirect handling so each hop is re-validated.
                current = url
                for _ in range(5):
                    resp = await client.get(current)
                    if resp.is_redirect and "location" in resp.headers:
                        current = str(resp.next_request.url) if resp.next_request else ""
                        check_url(current)
                        continue
                    body = resp.text[:_MAX_BYTES]
                    return redact(f"[{resp.status_code}] {current}\n{body}")
                return "çok fazla yönlendirme"
        except SSRFBlocked as exc:
            return f"engellendi (yönlendirme SSRF): {exc}"
        except httpx.HTTPError as exc:
            return f"ağ hatası: {exc}"

    return [
        Tool(
            name="web_fetch",
            description="Bir URL'nin içeriğini getirir (SSRF korumalı, salt-okunur).",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            handler=web_fetch,
            risk="caution",
        ),
    ]
