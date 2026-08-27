---
name: pytest-testing
description: Write and run tests with pytest
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
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# pytest
- **Run:** `pytest -q` ; single file `pytest tests/test_x.py`
- **Select:** `pytest -k "name expression"`
- **Stop on first fail:** `pytest -x` ; verbose `pytest -vv`
- **Coverage:** `pytest --cov=package`
- Share setup with **fixtures**; many cases with `@pytest.mark.parametrize`
- **Async:** `pytest-asyncio` + `@pytest.mark.asyncio`
