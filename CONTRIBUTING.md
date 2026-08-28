# Contributing to Milyonus Agent

Thanks for helping build a memory-safe, self-improving agent.

## Development setup

```bash
make sync                  # deps (matches CI: dev + admin + discord)
make hooks                 # enable the pre-push gate (runs the CI checks)
uv run milyonus doctor
uv run pytest -q
```

## Before you open a PR

Run `make check` — it mirrors CI exactly (`ruff check` · `ruff format --check` ·
`pytest`), so if it passes locally the pipeline will too. `make hooks` runs it
automatically on every push (bypass with `git push --no-verify`).

- `make check` — lint clean, **formatted** (CI runs `ruff format --check`, so an
  unformatted file fails the build — run `make fmt` to fix), tests green
- New behavior ships with tests. Security-relevant code ships with a test that
  fails if the guarantee is removed (see `tests/test_config.py`).

## Extending the agent

Add capability through the **skill**, **tool**, or **channel adapter**
interfaces — not by patching the core loop. See `PLAN.md` §2 and §4.
The core stays open and self-modifiable, but changes go through the `selfmod`
snapshot + test gate so they are always reversible.
