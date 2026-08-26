"""Run TaskBench tasks through the real agent, with a Tracer attached.

Lives inside the package so `milyonus eval` works for installed users. Each task
runs in an isolated temp workspace with only the safe fs + shell tools, is scored
by its programmatic check, and returns a RunTrace for aggregation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from milyonus.config.env import load_env
from milyonus.config.loader import load_config
from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.evaluation.tasks import Task
from milyonus.observability.trace import RunTrace, Tracer
from milyonus.prompt.builder import build_system_prompt
from milyonus.providers.base import Message
from milyonus.providers.router import build_provider
from milyonus.tools.fs.tools import make_fs_tools
from milyonus.tools.registry import ToolRegistry
from milyonus.tools.terminal.tools import make_shell_tool


async def run_task(task: Task, *, provider=None, max_iterations: int = 12) -> RunTrace:
    load_env()
    cfg = load_config()
    provider = provider or build_provider(cfg.provider)

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        for name, content in task.files.items():
            (ws / name).write_text(content, "utf-8")
        task.setup(ws)

        reg = ToolRegistry()
        for t in make_fs_tools(ws):
            reg.register(t)
        reg.register(make_shell_tool(ws))

        tracer = Tracer(task_id=task.id, model=provider.model)
        loop = AgentLoop(
            provider=provider,
            tools=reg,
            system_prompt=build_system_prompt(),
            budget=Budget(max_iterations=max_iterations),
            tracer=tracer,
            max_output_tokens=cfg.provider.max_output_tokens,
        )
        history = [Message(role="user", content=task.prompt)]
        try:
            await loop.run_turn(history)
            success = bool(task.check(ws))
            outcome = "ok" if success else "wrong-output"
        except Exception as exc:  # noqa: BLE001 - failures are data
            success, outcome = False, f"error: {type(exc).__name__}"
        return tracer.finish(success=success, outcome=outcome)
