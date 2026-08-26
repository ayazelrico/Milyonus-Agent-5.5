# Evaluation & observability

PoisonBench answers *"is it safe?"*. This answers the bigger production question:
**is the agent actually doing the job — and at what cost?**

Every run is traced, so a suite of tasks yields the numbers an operator lives by:
success rate, tool errors, redundant tool calls, tokens, wall-clock, USD cost,
and how often a human had to step in.

## Run it

```bash
milyonus eval tasks        # list the tasks
milyonus eval run          # run them through the real agent (needs a key)
```

Example report:

```
✦ TaskBench — 5 tasks
  ✓ create-file       ok   1846 tok · 1 tool · 5.9s
  ✓ read-and-answer   ok   2803 tok · 2 tool · 10.8s
  …
  Success rate         100.0%
  Tool calls           11   (errors 0 · redundant 0)
  Tokens (in/out)      14870 / 1151
  Wall-clock           0.68 min
  Cost                 $0.3094
  Human interventions  8
```

## How it works

- **Tracing** (`milyonus.observability.trace`) — a passive `Tracer` attaches to
  the agent loop and records every model call (tokens, latency, stop reason) and
  tool call (name, args, error, duration, whether it needed approval). Off by
  default; zero overhead when unused.
- **Cost** (`milyonus.observability.cost`) — a per-model price table turns tokens
  into USD. Prices are approximate and overridable with `set_price()`.
- **Report** (`milyonus.observability.report`) — aggregates many traces into the
  metrics above.
- **TaskBench** (`milyonus.evaluation`) — tasks are `{prompt, files, check}`.
  Each runs in an isolated temp workspace and is scored by a **programmatic
  check** (no LLM judge needed), so scores are deterministic and free to verify.

## Definitions

| Metric | Meaning |
|---|---|
| Success rate | tasks whose `check` passed / scored tasks |
| Tool errors | tool results returned as an error |
| Redundant tool calls | duplicate `(name, args)` invocations within a run |
| Human interventions | tool calls that required an approval decision |
| Cost | Σ tokens × per-model price (estimated when the model is unknown) |

## Extending

Add a task by appending to `milyonus/evaluation/tasks.py` with a `check` that
inspects the workspace. For subjective goals, wrap an LLM-as-judge inside a
`check` — the framework only needs a `bool`.
