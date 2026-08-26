# Contributing to Milyonus Agent

Thanks for helping build a memory-safe, self-improving agent.

## Development setup

```bash
uv sync --extra dev
uv run milyonus doctor
uv run pytest -q
```

## Before you open a PR

- `uv run ruff check src tests` — lint clean
- `uv run ruff format src tests` — formatted
- `uv run pytest -q` — tests green
- New behavior ships with tests. Security-relevant code ships with a test that
  fails if the guarantee is removed (see `tests/test_config.py`).

## Extending the agent

Add capability through the **skill**, **tool**, or **channel adapter**
interfaces — not by patching the core loop. See `PLAN.md` §2 and §4.
The core stays open and self-modifiable, but changes go through the `selfmod`
snapshot + test gate so they are always reversible.
