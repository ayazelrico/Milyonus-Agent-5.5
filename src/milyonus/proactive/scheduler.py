"""The scheduler runtime — the persistent process behind proactivity.

Design note parts 2–3: the scheduler is a plain OS-style component. It polls the
CronStore for due tasks, runs each through the agent (under the task's safety
policy), and delivers the result. It must stay running (VPS / systemd) for
"24/7" behavior — that is an infrastructure choice, not agent magic.

Delivery is injected: the CLI wires it to a channel adapter or stdout, so the
scheduler stays decoupled from any specific surface.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from milyonus.cron.store import CronStore, CronTask
from milyonus.observability.trace import RunTrace
from milyonus.proactive.runner import run_scheduled_task
from milyonus.providers.base import Provider

_log = logging.getLogger("milyonus.proactive")

# Called after a task runs: (task, answer, trace, denied_tools) -> None
Deliver = Callable[[CronTask, str, RunTrace, list[str]], Awaitable[None]]


async def _default_deliver(task: CronTask, answer: str, trace: RunTrace, denied: list[str]) -> None:
    _log.info("task %s (%s) -> %s", task.id, task.name, answer[:120])
    if denied:
        _log.info("task %s denied tools: %s", task.id, ", ".join(denied))


class Scheduler:
    def __init__(
        self,
        provider: Provider,
        *,
        workspace: Path,
        store: CronStore | None = None,
        deliver: Deliver | None = None,
        poll_seconds: float = 30.0,
    ) -> None:
        self.provider = provider
        self.workspace = workspace
        self.store = store or CronStore()
        self.deliver = deliver or _default_deliver
        self.poll_seconds = poll_seconds

    async def tick(self, now: float | None = None) -> list[str]:
        """Run all due tasks once. Returns the ids that ran."""
        ran: list[str] = []
        for task in self.store.due(now):
            _log.info("running due task %s (%s)", task.id, task.name)
            answer, trace, denied = await run_scheduled_task(
                task, provider=self.provider, workspace=self.workspace
            )
            await self.deliver(task, answer, trace, denied)
            self.store.mark_ran(task.id)
            ran.append(task.id)
        return ran

    async def run(self) -> None:
        """Poll forever, running due tasks. This is the long-lived process."""
        _log.info("scheduler started (poll every %.0fs)", self.poll_seconds)
        while True:
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001 - keep the scheduler alive
                _log.warning("scheduler tick error: %s", exc)
            await asyncio.sleep(self.poll_seconds)
