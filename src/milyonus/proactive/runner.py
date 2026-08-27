"""Run one scheduled task through the agent, unattended, under a safety policy.

Honest framing (design note part 3): proactivity is trigger-based execution — a
plain scheduler fires a task and the agent runs it. Because no human is present,
the approval policy is stricter than the interactive CLI:

  autonomy="safe-only"  (default) — only reversible/local tools auto-run;
      outward or irreversible tool calls are DENIED and logged. A scheduled task
      cannot silently send messages, delete data, or spend money unless the user
      pre-authorized it at creation.
  autonomy="authorized" — the user explicitly pre-approved outward/irreversible
      actions for this task; the RiskEngine still hard-blocks dangerous patterns
      (fork bombs, rm -rf /, curl|bash).

Every run is traced (tokens, tools, cost) so proactive automation is observable.
"""

from __future__ import annotations

from pathlib import Path

from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.cron.store import CronTask
from milyonus.observability.trace import RunTrace, Tracer
from milyonus.prompt.builder import build_system_prompt
from milyonus.providers.base import Message, Provider, ProviderError, ToolCall
from milyonus.security.risk import RiskEngine


def _policy_approver(autonomy: str, risk_engine: RiskEngine, denied: list[str]):
    async def approve(call: ToolCall, risk: str) -> bool:
        decision, reason, _ = risk_engine.classify(call, risk)
        if decision == "block":
            denied.append(f"{call.name} (blocked: {reason})")
            return False
        if decision == "auto":
            return True
        # decision == "confirm": needs a human. Only allowed if pre-authorized.
        if autonomy == "authorized":
            return True
        denied.append(f"{call.name} (needs approval, autonomy=safe-only)")
        return False

    return approve


async def run_scheduled_task(
    task: CronTask,
    *,
    provider: Provider,
    workspace: Path,
    max_output_tokens: int = 4096,
) -> tuple[str, RunTrace, list[str]]:
    """Run the task's prompt unattended. Returns (answer, trace, denied_tools)."""
    from milyonus.tools.fs.tools import make_fs_tools
    from milyonus.tools.registry import ToolRegistry
    from milyonus.tools.terminal.tools import make_shell_tool
    from milyonus.tools.web.tools import make_web_tools

    reg = ToolRegistry()
    for t in make_fs_tools(workspace):
        reg.register(t)
    reg.register(make_shell_tool(workspace))
    for t in make_web_tools():
        reg.register(t)

    denied: list[str] = []
    tracer = Tracer(task_id=task.id, model=provider.model)
    loop = AgentLoop(
        provider=provider,
        tools=reg,
        system_prompt=build_system_prompt(),
        budget=Budget(max_iterations=20),
        approve=_policy_approver(task.autonomy, RiskEngine(), denied),
        tracer=tracer,
        max_output_tokens=max_output_tokens,
    )
    history = [Message(role="user", content=task.prompt)]
    try:
        answer = await loop.run_turn(history)
        outcome = "ok"
    except ProviderError as exc:
        answer, outcome = f"Provider error: {exc}", "error"
    trace = tracer.finish(success=(outcome == "ok"), outcome=outcome)
    return answer, trace, denied
