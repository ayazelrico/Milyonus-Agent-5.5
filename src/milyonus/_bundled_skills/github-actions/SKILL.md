---
name: github-actions
description: GitHub Actions ile CI/CD workflow tasarımı (build, test, deploy)
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

Workflow dosyaları `.github/workflows/*.yml` içinde durur.

## İskelet
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

## Önemli desenler
- **Tetikleyiciler:** `push`, `pull_request`, `workflow_dispatch` (manuel), `schedule` (cron), `release`.
- **Matrix:** birden çok sürüm/OS'te koş:
  `strategy: { matrix: { python: ["3.11","3.12"] } }` → `${{ matrix.python }}`.
- **Cache:** `actions/cache@v4` ile bağımlılıkları hızlandır.
- **Secrets:** `${{ secrets.NAME }}` (Settings → Secrets'tan tanımla; loga yazma).
- **Koşul:** `if: github.ref == 'refs/heads/main'`.
- **İşler arası bağımlılık:** `needs: [test]`.
- **Artifact:** `actions/upload-artifact@v4` ile build çıktısı paylaş.

## İpuçları
- İş başına en az ayrıcalık; `permissions:` bloğuyla token kapsamını daralt.
- Üçüncü taraf action'ları SHA ile pinle (tedarik zinciri güvenliği).
- `concurrency:` ile eski koşuları iptal et.
