"""Dev entry point: `uv run python -m evals.taskbench.run`.

Delegates to the in-package runner so the CLI and this script stay in sync.
Set MILYONUS_LIVE=1 to actually run the agent (needs a provider key).
"""

from __future__ import annotations

import asyncio
import os


async def main() -> None:
    from milyonus.evaluation.tasks import TASKS

    if not os.environ.get("MILYONUS_LIVE"):
        print("✦ TaskBench tasks (set MILYONUS_LIVE=1 to run):")
        for t in TASKS:
            print(f"  [{t.category}] {t.id}: {t.prompt[:70]}")
        return

    from milyonus.evaluation.runner import run_task
    from milyonus.observability.report import aggregate

    traces = []
    for t in TASKS:
        tr = await run_task(t)
        print(
            f"  {'✓' if tr.success else '✗'} {t.id:16} {tr.total_tokens:>6} tok · {tr.duration_s:.1f}s"
        )
        traces.append(tr)
    print("\n── Evaluation report ──")
    print(aggregate(traces).table())


if __name__ == "__main__":
    asyncio.run(main())
