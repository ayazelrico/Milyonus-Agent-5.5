## What & why

<!-- What does this change and why? Link any issue. -->

## Checklist
- [ ] `uv run ruff check src tests` clean
- [ ] `uv run ruff format src tests` applied
- [ ] `uv run pytest -q` green
- [ ] New behavior has tests; security-relevant code has a test that fails if the
      guarantee is removed
- [ ] Extended via skill/tool/channel interfaces, not by patching the core loop
      (unless intentional and discussed)
