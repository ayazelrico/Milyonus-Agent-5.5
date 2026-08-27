---
name: security-audit
description: Audit dependencies, secrets and code security
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - security
    - audit
    - vulnerability
    - sast
    category: security
    requires_toolsets:
    - terminal
    provenance: official
---

# Security Audit
## Dependency vulnerabilities
```bash
pip-audit                     # Python (PyPI advisories)
npm audit --production        # Node
osv-scanner -r .              # multi-language (Google OSV)
trivy fs .                    # filesystem + image scan
```
## Secret leakage
```bash
gitleaks detect --source .    # search commit history for keys
trufflehog filesystem .       # verified secrets
```
- If found: **revoke/rotate** the key immediately, then purge from history (BFG/filter-repo).
## Static analysis (SAST)
```bash
bandit -r src/                # Python security linter
semgrep --config auto .       # rule-based, multi-language
ruff check --select S         # a subset of bandit rules
```
## Checklist (during code review)
- Input validation; parameterized queries for SQL (no injection).
- shell=True + user input in command execution = danger.
- SSRF: validate outbound URLs against private networks (Milyonus is fail-closed).
- Secrets in env/vault, not in code; redacted in logs.
- Least privilege; credential rotation.
- Pin dependencies + update regularly.
