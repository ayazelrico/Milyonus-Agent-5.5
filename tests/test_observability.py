"""Observability: tracer captures the loop, cost model, and aggregate report."""

from collections.abc import AsyncIterator

import pytest

from milyonus.core.loop import AgentLoop
from milyonus.observability.cost import cost_of, set_price
from milyonus.observability.report import aggregate
from milyonus.observability.trace import Tracer
from milyonus.providers.base import CompletionRequest, StreamEvent, ToolCall, Usage
from milyonus.tools.registry import Tool, ToolRegistry


class Scripted:
    name = "fake"
    model = "claude-opus-4-8"

    def __init__(self, batches):
        self._b = batches
        self._i = 0

    async def stream(self, req: CompletionRequest) -> AsyncIterator[StreamEvent]:
        batch = self._b[self._i]
        self._i += 1
        for ev in batch:
            yield ev


def _text(s):
    return StreamEvent(kind="text", delta=s)


def _call(name, args, cid="c1"):
    return StreamEvent(kind="tool_call", tool_call=ToolCall(id=cid, name=name, arguments=args))


def _end(inp=100, out=20, stop="end_turn"):
    return [
        StreamEvent(kind="usage", usage=Usage(input_tokens=inp, output_tokens=out)),
        StreamEvent(kind="done", stop_reason=stop),
    ]


def _reg(seen):
    reg = ToolRegistry()

    async def echo(args):
        seen.append(args)
        return "ok"

    reg.register(
        Tool(
            name="echo",
            description="d",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=echo,
            risk="safe",
        )
    )
    return reg


# --- cost ---------------------------------------------------------------


def test_cost_known_model():
    c = cost_of("claude-opus-4-8", 1_000_000, 1_000_000)
    assert c.usd == pytest.approx(15.0 + 75.0)
    assert c.estimated is False


def test_cost_unknown_model_estimated():
    c = cost_of("mystery-model", 1_000_000, 0)
    assert c.estimated is True
    assert c.usd > 0


def test_set_price_override():
    set_price("test-model", 2.0, 4.0)
    c = cost_of("test-model", 1_000_000, 1_000_000)
    assert c.usd == pytest.approx(6.0)


# --- tracer via the loop ------------------------------------------------


async def test_tracer_captures_tokens_and_tools():
    seen = []
    prov = Scripted(
        [
            [_call("echo", {"x": "hi"}), *_end(inp=100, out=20, stop="tool_use")],
            [_text("done"), *_end(inp=50, out=10)],
        ]
    )
    tracer = Tracer(task_id="t1", model=prov.model)
    loop = AgentLoop(prov, _reg(seen), "sys", tracer=tracer)
    await loop.run_turn([])
    tr = tracer.finish(success=True)
    assert tr.input_tokens == 150
    assert tr.output_tokens == 30
    assert tr.total_tokens == 180
    assert tr.n_model_calls == 2
    assert tr.n_tool_calls == 1
    assert tr.tool_errors == 0
    assert tr.success is True


async def test_tracer_counts_redundant_calls():
    seen = []
    prov = Scripted(
        [
            [_call("echo", {"x": "same"}), *_end(stop="tool_use")],
            [_call("echo", {"x": "same"}), *_end(stop="tool_use")],  # duplicate
            [_text("done"), *_end()],
        ]
    )
    tracer = Tracer(model="claude-opus-4-8")
    loop = AgentLoop(prov, _reg(seen), "sys", tracer=tracer)
    await loop.run_turn([])
    tr = tracer.finish(success=True)
    assert tr.n_tool_calls == 2
    assert tr.redundant_tool_calls == 1


async def test_tracer_human_intervention_on_danger():
    reg = ToolRegistry()

    async def rm(args):
        return "removed"

    reg.register(
        Tool(name="rm", description="d", parameters={"type": "object"}, handler=rm, risk="danger")
    )

    async def approve(call, risk):
        return True  # a human said yes

    prov = Scripted(
        [
            [_call("rm", {}), *_end(stop="tool_use")],
            [_text("done"), *_end()],
        ]
    )
    tracer = Tracer(model="claude-opus-4-8")
    loop = AgentLoop(prov, reg, "sys", approve=approve, tracer=tracer)
    await loop.run_turn([])
    tr = tracer.finish(success=True)
    assert tr.human_interventions == 1


# --- aggregate report ---------------------------------------------------


async def test_aggregate_report():
    traces = []
    for i in range(3):
        prov = Scripted([[_text("x"), *_end(inp=100, out=20)]])
        tracer = Tracer(task_id=f"t{i}", model="claude-opus-4-8")
        loop = AgentLoop(prov, ToolRegistry(), "sys", tracer=tracer)
        await loop.run_turn([])
        traces.append(tracer.finish(success=(i != 2)))  # 2 pass, 1 fail
    rep = aggregate(traces)
    assert rep.n_tasks == 3
    assert rep.n_success == 2 and rep.n_fail == 1
    assert rep.success_rate == pytest.approx(2 / 3)
    assert rep.total_tokens == 360  # 3 × 120
    assert rep.usd > 0
