---
name: github-actions
description: Design CI/CD workflows with GitHub Actions (build, test, deploy)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - ci
    - cd
    - github
    - actions
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# GitHub Actions
Workflow files live in `.github/workflows/*.yml`.
## Skeleton
```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e .[dev]
      - run: pytest -q
```
## Key patterns
- **Triggers:** `push`, `pull_request`, `workflow_dispatch` (manual), `schedule` (cron), `release`.
- **Matrix:** run across versions/OSes: `strategy: { matrix: { python: ["3.11","3.12"] } }` -> `${{ matrix.python }}`.
- **Cache:** speed up deps with `actions/cache@v4`.
- **Secrets:** `${{ secrets.NAME }}` (define under Settings -> Secrets; never log).
- **Condition:** `if: github.ref == 'refs/heads/main'`.
- **Job deps:** `needs: [test]`.
- **Artifacts:** share build output with `actions/upload-artifact@v4`.
## Tips
- Least privilege per job; narrow the token with a `permissions:` block.
- Pin third-party actions by SHA (supply-chain safety).
- Cancel stale runs with `concurrency:`.
