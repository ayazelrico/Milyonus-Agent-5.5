"""The `schedule_task` tool — lets the agent turn a request into a standing rule.

When the user says "every morning send me a report", the agent calls this to
create a scheduled task. Creating a standing rule is side-effectful, so the tool
is classified "caution" → it routes through the approval flow. Tasks default to
safe-only autonomy; outward/irreversible unattended actions require the user to
opt in explicitly.
"""

from __future__ import annotations

from typing import Any

from milyonus.cron.schedule import ScheduleError, parse_schedule
from milyonus.cron.store import CronStore
from milyonus.tools.registry import Tool


def make_schedule_tool(store: CronStore | None = None) -> Tool:
    store = store or CronStore()

    async def schedule_task(args: dict[str, Any]) -> str:
        name = args["name"].strip()
        when = args["when"].strip()
        prompt = args["prompt"].strip()
        try:
            sched = parse_schedule(when)
        except ScheduleError as exc:
            return f"could not schedule: {exc}"
        authorized = bool(args.get("authorized", False))
        tid = store.add(
            name,
            when,
            prompt,
            channel=args.get("channel"),
            autonomy="authorized" if authorized else "safe-only",
        )
        note = " (authorized for outward actions)" if authorized else " (safe-only)"
        return f"scheduled '{name}' ({sched.display}){note} — id {tid}"

    return Tool(
        name="schedule_task",
        description=(
            "Create a recurring scheduled task. `when` accepts an interval "
            "('30m'), a cron expression ('0 9 * * *'), or natural language "
            "('every day at 9:00'). Default autonomy is safe-only; set "
            "authorized=true only if the user explicitly approved unattended "
            "outward/irreversible actions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "when": {"type": "string", "description": "Schedule spec"},
                "prompt": {"type": "string", "description": "What to do each time"},
                "authorized": {"type": "boolean"},
            },
            "required": ["name", "when", "prompt"],
        },
        handler=schedule_task,
        risk="caution",  # creating a standing rule -> approval flow
    )
