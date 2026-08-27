---
name: python-uv
description: Manage Python projects, venvs and deps with uv
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - python
    - uv
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# Python + uv
- **Init project:** `uv init` ; pin Python `uv python pin 3.12`
- **Deps:** `uv add package` ; dev `uv add --dev pytest`
- **Sync:** `uv sync` (install the locked env)
- **Run:** `uv run python script.py` / `uv run pytest`
- **Install a tool:** `uv tool install ruff`
- **Lock:** `uv lock`
