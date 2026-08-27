"""Anthropic Messages API provider (default backend, ADR-002).

Implemented directly on httpx to keep the dependency surface small and to own
streaming/cancellation. Translates neutral Message/ToolCall/ToolResult types to
and from the Anthropic wire format.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

from milyonus.providers.base import (
    CompletionRequest,
    Message,
    ProviderError,
    StreamEvent,
    ToolCall,
    Usage,
)

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


def _to_wire_messages(messages: list[Message]) -> list[dict]:
    """Translate neutral messages into Anthropic's content-block format."""
    wire: list[dict] = []
    for msg in messages:
        if msg.role == "tool":
            # Tool results are sent as a user turn with tool_result blocks.
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": r.call_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in msg.tool_results
            ]
            wire.append({"role": "user", "content": blocks})
            continue

        blocks = []
        for img in msg.images:
            blocks.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": img.media_type, "data": img.data},
                }
            )
        if msg.content:
            blocks.append({"type": "text", "text": msg.content})
        for call in msg.tool_calls:
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.arguments,
                }
            )
        wire.append({"role": msg.role, "content": blocks or msg.content})
    return wire


class AnthropicProvider:
    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "anthropic"
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._url = (base_url or _API_URL).rstrip("/")
        if base_url and not self._url.endswith("/messages"):
            self._url = f"{self._url}/v1/messages"
        self._client = client

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set. Add it to `~/.milyonus/.env`.")
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

    def _payload(self, request: CompletionRequest) -> dict:
        payload: dict = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system,
            "messages": _to_wire_messages(list(request.messages)),
            "stream": True,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in request.tools
            ]
        # Note: newer Anthropic models deprecate `temperature`; we omit it and
        # let the model use its default. (OpenAI-compatible still honors it.)
        return payload

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        owns_client = self._client is None
        # Accumulator for the tool_use block currently being streamed.
        cur_tool: dict | None = None
        cur_json: list[str] = []
        usage = Usage()
        try:
            async with client.stream(
                "POST", self._url, headers=self._headers(), json=self._payload(request)
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise ProviderError(f"Anthropic {resp.status_code}: {body[:500]}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data:
                        continue
                    event = json.loads(data)
                    etype = event.get("type")
                    if etype == "message_start":
                        u = event["message"].get("usage", {})
                        usage.input_tokens = u.get("input_tokens", 0)
                    elif etype == "content_block_start":
                        block = event["content_block"]
                        if block["type"] == "tool_use":
                            cur_tool = {"id": block["id"], "name": block["name"]}
                            cur_json = []
                    elif etype == "content_block_delta":
                        delta = event["delta"]
                        if delta["type"] == "text_delta":
                            yield StreamEvent(kind="text", delta=delta["text"])
                        elif delta["type"] == "input_json_delta":
                            cur_json.append(delta["partial_json"])
                    elif etype == "content_block_stop":
                        if cur_tool is not None:
                            raw = "".join(cur_json) or "{}"
                            args = json.loads(raw) if raw.strip() else {}
                            yield StreamEvent(
                                kind="tool_call",
                                tool_call=ToolCall(
                                    id=cur_tool["id"],
                                    name=cur_tool["name"],
                                    arguments=args,
                                ),
                            )
                            cur_tool = None
                    elif etype == "message_delta":
                        u = event.get("usage", {})
                        usage.output_tokens = u.get("output_tokens", usage.output_tokens)
                        stop = event.get("delta", {}).get("stop_reason")
                        if stop:
                            yield StreamEvent(kind="usage", usage=usage)
                            yield StreamEvent(kind="done", stop_reason=stop)
        finally:
            if owns_client:
                await client.aclose()
