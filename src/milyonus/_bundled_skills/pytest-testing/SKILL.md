---
name: pytest-testing
description: pytest ile test yazma ve çalıştırma
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - python
    - test
    - pytest
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# pytest
- **Çalıştır:** `pytest -q` ; tek dosya `pytest tests/test_x.py`
- **Seç:** `pytest -k "isim ifadesi"`
- **İlk hatada dur:** `pytest -x` ; ayrıntı `pytest -vv`
- **Kapsam:** `pytest --cov=paket`
- **Fixture** ile kurulum paylaş; `@pytest.mark.parametrize` ile çok senaryo
- **Async:** `pytest-asyncio` + `@pytest.mark.asyncio`
