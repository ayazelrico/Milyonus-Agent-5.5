"""Aggregate many run traces into the metrics a production agent is judged on.

Answers the operator's questions across a suite:
  how many tasks succeeded / failed · tool errors · redundant tool calls ·
  tokens · wall-clock minutes · USD cost · human interventions.
"""

from __future__ import annotations

from dataclasses import dataclass

from milyonus.observability.cost import cost_of
from milyonus.observability.trace import RunTrace


@dataclass(slots=True)
class Report:
    n_tasks: int
    n_success: int
    n_fail: int
    n_unscored: int
    success_rate: float
    tool_calls: int
    tool_errors: int
    redundant_tool_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    minutes: float
    usd: float
    usd_estimated: bool
    human_interventions: int

    def table(self) -> str:
        rows = [
            ("Tasks", f"{self.n_tasks}"),
            ("  succeeded", f"{self.n_success}"),
            ("  failed", f"{self.n_fail}"),
            ("  unscored", f"{self.n_unscored}"),
            ("Success rate", f"{self.success_rate:.1%}"),
            ("Tool calls", f"{self.tool_calls}"),
            ("  tool errors", f"{self.tool_errors}"),
            ("  redundant calls", f"{self.redundant_tool_calls}"),
            ("Tokens (in/out)", f"{self.input_tokens} / {self.output_tokens}"),
            ("Tokens total", f"{self.total_tokens}"),
            ("Wall-clock", f"{self.minutes:.2f} min"),
            ("Cost", f"${self.usd:.4f}{' (est.)' if self.usd_estimated else ''}"),
            ("Human interventions", f"{self.human_interventions}"),
        ]
        width = max(len(k) for k, _ in rows)
        return "\n".join(f"  {k.ljust(width)}  {v}" for k, v in rows)


def aggregate(traces: list[RunTrace]) -> Report:
    scored = [t for t in traces if t.success is not None]
    n_success = sum(1 for t in traces if t.success is True)
    n_fail = sum(1 for t in traces if t.success is False)
    n_unscored = len(traces) - len(scored)

    usd_total = 0.0
    usd_estimated = False
    for t in traces:
        c = cost_of(t.model, t.input_tokens, t.output_tokens)
        usd_total += c.usd
        usd_estimated = usd_estimated or c.estimated

    return Report(
        n_tasks=len(traces),
        n_success=n_success,
        n_fail=n_fail,
        n_unscored=n_unscored,
        success_rate=(n_success / len(scored)) if scored else 0.0,
        tool_calls=sum(t.n_tool_calls for t in traces),
        tool_errors=sum(t.tool_errors for t in traces),
        redundant_tool_calls=sum(t.redundant_tool_calls for t in traces),
        input_tokens=sum(t.input_tokens for t in traces),
        output_tokens=sum(t.output_tokens for t in traces),
        total_tokens=sum(t.total_tokens for t in traces),
        minutes=sum(t.duration_s for t in traces) / 60.0,
        usd=round(usd_total, 6),
        usd_estimated=usd_estimated,
        human_interventions=sum(t.human_interventions for t in traces),
    )
