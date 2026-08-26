---
name: python-uv
description: uv ile Python proje, sanal ortam ve bağımlılık yönetimi
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - python
    - uv
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# Python + uv
- **Proje başlat:** `uv init` ; Python sabitle `uv python pin 3.12`
- **Bağımlılık:** `uv add paket` ; geliştirme `uv add --dev pytest`
- **Senkron:** `uv sync` (kilitli ortamı kur)
- **Çalıştır:** `uv run python script.py` / `uv run pytest`
- **Araç kur:** `uv tool install ruff`
- **Kilitle:** `uv lock`
