---
name: github-cli
description: Manage PRs, issues and repos with the GitHub CLI (gh)
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
- **Auth:** `gh auth status` (login: `gh auth login`)
- **Open a PR:** `gh pr create --fill` (current branch -> target); draft `--draft`
- **Review a PR:** `gh pr view`, `gh pr diff`, `gh pr checks`
- **Issues:** `gh issue list --state open`, `gh issue create --title ... --body ...`
- **Clone:** `gh repo clone owner/repo`
- **CI status:** `gh run list`, `gh run watch`
