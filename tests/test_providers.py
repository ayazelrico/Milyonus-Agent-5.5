"""Provider adapters are tested against recorded SSE streams — no live API,
so CI is green without any key. This is the VCR foundation for the agent loop."""

import httpx
import pytest

from milyonus.config.schema import ProviderConfig
from milyonus.providers import CompletionRequest, Message, build_provider
from milyonus.providers.anthropic import AnthropicProvider
from milyonus.providers.openai_compat import OpenAICompatProvider

ANTHROPIC_SSE = (
    'data: {"type":"message_start","message":{"usage":{"input_tokens":10}}}\n'
    "\n"
    'data: {"type":"content_block_start","index":0,'
    '"content_block":{"type":"text","text":""}}\n'
    "\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":"Merhaba"}}\n'
    "\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":" dünya"}}\n'
    "\n"
    'data: {"type":"content_block_stop","index":0}\n'
    "\n"
    'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},'
    '"usage":{"output_tokens":5}}\n'
    "\n"
)

ANTHROPIC_TOOL_SSE = (
    'data: {"type":"message_start","message":{"usage":{"input_tokens":8}}}\n\n'
    'data: {"type":"content_block_start","index":0,'
    '"content_block":{"type":"tool_use","id":"tu_1","name":"read_file"}}\n\n'
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"input_json_delta","partial_json":"{\\"path\\":"}}\n\n'
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"input_json_delta","partial_json":"\\"a.txt\\"}"}}\n\n'
    'data: {"type":"content_block_stop","index":0}\n\n'
    'data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},'
    '"usage":{"output_tokens":12}}\n\n'
)

OPENAI_SSE = (
    'data: {"choices":[{"delta":{"content":"Merhaba"},"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{"content":" dünya"},"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
    '"usage":{"prompt_tokens":10,"completion_tokens":5}}\n\n'
    "data: [DONE]\n\n"
)

OPENAI_TOOL_SSE = (
    'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1",'
    '"function":{"name":"read_file","arguments":"{\\"path\\":"}}]},'
    '"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
    '"function":{"arguments":"\\"a.txt\\"}"}}]},"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}],'
    '"usage":{"prompt_tokens":8,"completion_tokens":12}}\n\n'
)


def _client_returning(sse: str) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=sse)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _req() -> CompletionRequest:
    return CompletionRequest(system="s", messages=[Message(role="user", content="hi")])


async def _collect(provider, req):
    text, tools, usage, stop = "", [], None, None
    async for ev in provider.stream(req):
        if ev.kind == "text":
            text += ev.delta
        elif ev.kind == "tool_call":
            tools.append(ev.tool_call)
        elif ev.kind == "usage":
            usage = ev.usage
        elif ev.kind == "done":
            stop = ev.stop_reason
    return text, tools, usage, stop


async def test_anthropic_text():
    p = AnthropicProvider("m", api_key="k", client=_client_returning(ANTHROPIC_SSE))
    text, tools, usage, stop = await _collect(p, _req())
    assert text == "Merhaba dünya"
    assert not tools
    assert usage.input_tokens == 10 and usage.output_tokens == 5
    assert stop == "end_turn"


async def test_anthropic_tool_call():
    p = AnthropicProvider("m", api_key="k", client=_client_returning(ANTHROPIC_TOOL_SSE))
    _, tools, _, stop = await _collect(p, _req())
    assert len(tools) == 1
    assert tools[0].name == "read_file"
    assert tools[0].arguments == {"path": "a.txt"}
    assert stop == "tool_use"


async def test_openai_text():
    p = OpenAICompatProvider("m", api_key="k", client=_client_returning(OPENAI_SSE))
    text, _, usage, stop = await _collect(p, _req())
    assert text == "Merhaba dünya"
    assert usage.input_tokens == 10 and usage.output_tokens == 5
    assert stop == "stop"


async def test_openai_tool_call():
    p = OpenAICompatProvider("m", api_key="k", client=_client_returning(OPENAI_TOOL_SSE))
    _, tools, _, stop = await _collect(p, _req())
    assert len(tools) == 1
    assert tools[0].name == "read_file"
    assert tools[0].arguments == {"path": "a.txt"}
    assert stop == "tool_calls"


def test_router_openrouter_key_env():
    from milyonus.providers.router import openrouter_config

    p = build_provider(openrouter_config("openai/gpt-4o"))
    assert p.name == "openai"
    assert "openrouter" in p._url


def test_router_local_needs_no_key():
    p = build_provider(ProviderConfig(name="local", model="llama3", base_url=None))
    # Should construct without OPENAI_API_KEY set.
    assert p.name == "openai"


def test_missing_key_errors(monkeypatch):
    from milyonus.providers.base import ProviderError

    # api_key="" falls back to the environment; ensure it is truly absent.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicProvider("m", api_key="")
    with pytest.raises(ProviderError):
        p._headers()
