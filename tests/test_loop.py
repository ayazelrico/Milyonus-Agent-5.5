"""AgentLoop: tool round-trips, approval gating, and budget stop — all with a
scripted fake provider so no API is touched."""

from collections.abc import AsyncIterator

from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.providers.base import (
    CompletionRequest,
    StreamEvent,
    ToolCall,
    Usage,
)
from milyonus.tools.registry import Tool, ToolRegistry


class ScriptedProvider:
    """Yields a pre-programmed list of event-batches, one batch per model call."""

    name = "fake"
    model = "fake"

    def __init__(self, batches: list[list[StreamEvent]]):
        self._batches = batches
        self._i = 0

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        batch = self._batches[self._i]
        self._i += 1
        for ev in batch:
            yield ev


def _text(s: str) -> StreamEvent:
    return StreamEvent(kind="text", delta=s)


def _call(name: str, args: dict, cid: str = "c1") -> StreamEvent:
    return StreamEvent(kind="tool_call", tool_call=ToolCall(id=cid, name=name, arguments=args))


def _end(stop: str = "end_turn", out: int = 5) -> list[StreamEvent]:
    return [
        StreamEvent(kind="usage", usage=Usage(input_tokens=10, output_tokens=out)),
        StreamEvent(kind="done", stop_reason=stop),
    ]


def _registry_with(calls_seen: list) -> ToolRegistry:
    reg = ToolRegistry()

    async def echo(args):
        calls_seen.append(args)
        return f"echoed:{args.get('x')}"

    reg.register(
        Tool(
            name="echo",
            description="echoes",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=echo,
            risk="safe",
        )
    )
    return reg


async def test_simple_text_turn():
    prov = ScriptedProvider([[_text("Merhaba"), *_end()]])
    loop = AgentLoop(prov, ToolRegistry(), "sys")
    hist = []
    result = await loop.run_turn(hist)
    assert result == "Merhaba"
    assert hist[-1].role == "assistant"


async def test_tool_then_final():
    seen = []
    prov = ScriptedProvider(
        [
            [_call("echo", {"x": "hi"}), *_end(stop="tool_use")],
            [_text("bitti"), *_end()],
        ]
    )
    loop = AgentLoop(prov, _registry_with(seen), "sys")
    hist = []
    result = await loop.run_turn(hist)
    assert result == "bitti"
    assert seen == [{"x": "hi"}]
    # history: assistant(call) -> tool(result) -> assistant(final)
    roles = [m.role for m in hist]
    assert roles == ["assistant", "tool", "assistant"]


async def test_danger_tool_denied():
    seen = []
    reg = ToolRegistry()

    async def rm(args):
        seen.append(args)
        return "deleted"

    reg.register(
        Tool(
            name="rm",
            description="removes",
            parameters={"type": "object", "properties": {}},
            handler=rm,
            risk="danger",
        )
    )

    async def deny(call, risk):
        return False

    prov = ScriptedProvider(
        [
            [_call("rm", {}), *_end(stop="tool_use")],
            [_text("iptal edildi"), *_end()],
        ]
    )
    loop = AgentLoop(prov, reg, "sys", approve=deny)
    hist = []
    result = await loop.run_turn(hist)
    assert result == "iptal edildi"
    assert seen == []  # handler never ran
    assert hist[1].tool_results[0].is_error is True


async def test_budget_stop():
    prov = ScriptedProvider([[_text("x"), *_end()]])
    loop = AgentLoop(prov, ToolRegistry(), "sys", budget=Budget(max_iterations=0))
    result = await loop.run_turn([])
    assert "bütçe" in result


async def test_streaming_sink():
    chunks = []

    async def sink(s):
        chunks.append(s)

    prov = ScriptedProvider([[_text("ab"), _text("cd"), *_end()]])
    loop = AgentLoop(prov, ToolRegistry(), "sys", on_text=sink)
    await loop.run_turn([])
    assert chunks == ["ab", "cd"]
