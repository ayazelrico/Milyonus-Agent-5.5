"""OpenAI-compatible provider — covers OpenAI, OpenRouter, and local vLLM.

All three speak the OpenAI Chat Completions API; only the base_url and the env
var holding the key differ. One adapter serves them by translating the neutral
message types to and from OpenAI's tool-calling format.
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

# Well-known endpoints. Any OpenAI-compatible base_url works.
OPENAI_URL = "https://api.openai.com/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"


def _to_wire_messages(system: str, messages: list[Message]) -> list[dict]:
    wire: list[dict] = [{"role": "system", "content": system}]
    for msg in messages:
        if msg.role == "tool":
            for r in msg.tool_results:
                wire.append(
                    {
                        "role": "tool",
                        "tool_call_id": r.call_id,
                        "content": r.content,
                    }
                )
            continue
        if msg.images:
            content_parts: list[dict] = []
            if msg.content:
                content_parts.append({"type": "text", "text": msg.content})
            for img in msg.images:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{img.media_type};base64,{img.data}"},
                    }
                )
            entry: dict = {"role": msg.role, "content": content_parts}
        else:
            entry = {"role": msg.role, "content": msg.content or None}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {
                        "name": c.name,
                        "arguments": json.dumps(c.arguments),
                    },
                }
                for c in msg.tool_calls
            ]
        wire.append(entry)
    return wire


class OpenAICompatProvider:
    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "openai"
        self.model = model
        self._url = (base_url or OPENAI_URL).rstrip("/")
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._api_key_env = api_key_env
        self._client = client

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError(f"{self._api_key_env} is not set. Add it to `~/.milyonus/.env`.")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        # OpenRouter appreciates attribution headers; harmless elsewhere.
        if "openrouter" in self._url:
            headers["HTTP-Referer"] = "https://github.com/milyonus/milyonus-agent"
            headers["X-Title"] = "Milyonus Agent"
        return headers

    def _payload(self, request: CompletionRequest) -> dict:
        payload: dict = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "messages": _to_wire_messages(request.system, list(request.messages)),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in request.tools
            ]
        if request.temperature != 1.0:
            payload["temperature"] = request.temperature
        return payload

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        owns_client = self._client is None
        # tool_calls arrive as indexed deltas; assemble by index.
        tools: dict[int, dict] = {}
        usage = Usage()
        try:
            async with client.stream(
                "POST",
                f"{self._url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request),
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise ProviderError(f"OpenAI {resp.status_code}: {body[:500]}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data or data == "[DONE]":
                        continue
                    event = json.loads(data)
                    if event.get("usage"):
                        u = event["usage"]
                        usage.input_tokens = u.get("prompt_tokens", usage.input_tokens)
                        usage.output_tokens = u.get("completion_tokens", usage.output_tokens)
                    for choice in event.get("choices", []):
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            yield StreamEvent(kind="text", delta=delta["content"])
                        for tc in delta.get("tool_calls", []):
                            idx = tc.get("index", 0)
                            slot = tools.setdefault(idx, {"id": "", "name": "", "args": ""})
                            if tc.get("id"):
                                slot["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["args"] += fn["arguments"]
                        finish = choice.get("finish_reason")
                        if finish:
                            for slot in tools.values():
                                if slot["name"]:
                                    raw = slot["args"] or "{}"
                                    args = json.loads(raw) if raw.strip() else {}
                                    yield StreamEvent(
                                        kind="tool_call",
                                        tool_call=ToolCall(
                                            id=slot["id"], name=slot["name"], arguments=args
                                        ),
                                    )
                            yield StreamEvent(kind="usage", usage=usage)
                            yield StreamEvent(kind="done", stop_reason=finish)
        finally:
            if owns_client:
                await client.aclose()
