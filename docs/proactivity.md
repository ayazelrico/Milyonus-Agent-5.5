# Proactivity

Milyonus can act on triggers and suggest automations. It's worth being precise
about the mechanism, because "proactivity" is often oversold.

## What it actually is

Proactivity here is **trigger-based execution + history-based automation
suggestion** — not foresight. The system does not predict the future; a plain
scheduler fires tasks, and the agent detects *past repetition* to propose rules.

Three classic components around the LLM:

1. **Orchestrator** — the LLM plans and, crucially, compiles natural language
   into a structured schedule ("every morning" → `0 9 * * *`).
2. **Scheduler** — a plain OS-style component that polls for due tasks and fires
   them. It must stay running (VPS/systemd) for 24/7 behavior — that is an
   infrastructure choice, not agent magic.
3. **Persistent memory / skills** — verified memory + self-authored skills feed
   future runs (see the memory and skills docs).

The genuinely new part is not autonomy; it's that the orchestrator can be driven
in natural language and can write its own rule set — with a human in the loop for
anything side-effectful.

## Scheduled tasks

```bash
# natural language, cron, or interval all work
milyonus cron add "report" "every day at 9:00" "Summarize yesterday's commits"
milyonus cron add "ping"   "*/30 * * * *"      "Check the health endpoint"
milyonus cron add "sync"   "2h"                "Pull new issues"

milyonus cron list
milyonus cron remove <id>

# run the scheduler (long-lived process)
milyonus proactive start --workspace .
```

The agent can also schedule from a conversation via the `schedule_task` tool —
"every morning send me a report" creates a task, gated by the approval flow
because a standing rule is a side-effectful change.

## Safety policy for unattended runs

Because no human is present when a scheduled task fires, autonomy is stricter
than the interactive CLI:

| Autonomy | Behavior |
|---|---|
| **safe-only** (default) | Only reversible/local tools auto-run. Outward or irreversible tool calls are **denied and logged** — a task can't silently send messages, delete data, or spend money. |
| **authorized** (`--authorized`) | The user pre-approved outward/irreversible actions for this task. The RiskEngine still hard-blocks dangerous patterns (fork bombs, `rm -rf /`, `curl \| bash`). |

Every scheduled run is traced (tokens, tools, cost) — proactive automation is
observable, like everything else (`milyonus eval`).

## Automation suggestions

```bash
milyonus proactive suggest
```

Scans the session history for **repeated** requests and proposes turning them
into a scheduled task or a skill. Suggestions are never auto-applied — you create
one explicitly with `milyonus cron add`. This is repetition detection, honestly
labeled, not prediction.
