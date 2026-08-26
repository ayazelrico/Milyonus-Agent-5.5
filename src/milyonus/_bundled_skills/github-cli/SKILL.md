---
name: github-cli
description: GitHub CLI (gh) ile PR, issue ve repo yönetimi
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - github
    - gh
    - pr
    category: git
    requires_toolsets:
    - terminal
    provenance: official
---

# GitHub CLI (gh)
- **Kimlik:** `gh auth status` (giriş: `gh auth login`)
- **PR aç:** `gh pr create --fill` (mevcut dal → hedef); taslak `--draft`
- **PR gözden geçir:** `gh pr view`, `gh pr diff`, `gh pr checks`
- **Issue:** `gh issue list --state open`, `gh issue create --title ... --body ...`
- **Repo klonla:** `gh repo clone owner/repo`
- **CI durumu:** `gh run list`, `gh run watch`
