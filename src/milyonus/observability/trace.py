"""Execution tracing for the agent loop.

A Tracer records structured events during a run — model calls, tool calls, and
approval decisions — so a run can be scored on the questions production agents
actually care about: did it succeed, how many tool errors, how many redundant
calls, how many tokens, how long, how much money, how many human interventions.

The Tracer is passive: the AgentLoop calls its `on_*` methods at points it
already has. It holds no I/O, so it is cheap and unit-testable. Persistence and
aggregation live in `store.py` and `report.py`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class ModelCall:
    input_tokens: int
    output_tokens: int
    latency_s: float
    stop_reason: str | None = None


@dataclass(slots=True)
class ToolCallRecord:
    name: str
    arguments: dict
    is_error: bool
    duration_s: float
    approved: bool | None = None  # None = no approval needed; True/False = decision


@dataclass(slots=True)
class RunTrace:
    """Everything observed for a single task/run."""

    task_id: str = ""
    model: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    model_calls: list[ModelCall] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    # Set by the harness after scoring.
    success: bool | None = None
    outcome: str = ""

    # --- derived metrics ------------------------------------------------

    @property
    def input_tokens(self) -> int:
        return sum(m.input_tokens for m in self.model_calls)

    @property
    def output_tokens(self) -> int:
        return sum(m.output_tokens for m in self.model_calls)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def duration_s(self) -> float:
        return (self.ended_at or time.time()) - self.started_at

    @property
    def n_model_calls(self) -> int:
        return len(self.model_calls)

    @property
    def n_tool_calls(self) -> int:
        return len(self.tool_calls)

    @property
    def tool_errors(self) -> int:
        return sum(1 for t in self.tool_calls if t.is_error)

    @property
    def human_interventions(self) -> int:
        """Tool calls that required a human approval decision."""
        return sum(1 for t in self.tool_calls if t.approved is not None)

    @property
    def redundant_tool_calls(self) -> int:
        """Duplicate (name, arguments) tool invocations within the run — a
        heuristic for wasted work. The first occurrence is not counted."""
        seen: set[tuple] = set()
        dupes = 0
        for t in self.tool_calls:
            key = (t.name, _freeze(t.arguments))
            if key in seen:
                dupes += 1
            else:
                seen.add(key)
        return dupes


def _freeze(obj) -> object:
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


class Tracer:
    """Collects events for one run. Passed to AgentLoop; safe to reuse per task."""

    def __init__(self, *, task_id: str = "", model: str = "") -> None:
        self.trace = RunTrace(task_id=task_id, model=model)
        self._call_start: float | None = None

    def start_model_call(self) -> None:
        self._call_start = time.perf_counter()

    def end_model_call(
        self, *, input_tokens: int, output_tokens: int, stop_reason: str | None
    ) -> None:
        latency = time.perf_counter() - (self._call_start or time.perf_counter())
        self.trace.model_calls.append(ModelCall(input_tokens, output_tokens, latency, stop_reason))
        self._call_start = None

    def record_tool_call(
        self,
        *,
        name: str,
        arguments: dict,
        is_error: bool,
        duration_s: float,
        approved: bool | None,
    ) -> None:
        self.trace.tool_calls.append(
            ToolCallRecord(name, arguments, is_error, duration_s, approved)
        )

    def finish(self, *, success: bool | None = None, outcome: str = "") -> RunTrace:
        self.trace.ended_at = time.time()
        if success is not None:
            self.trace.success = success
        self.trace.outcome = outcome
        return self.trace
