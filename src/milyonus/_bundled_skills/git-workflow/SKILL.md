---
name: git-workflow
description: Git branching, commit, rebase and conflict-resolution workflow
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - git
    - vcs
    category: git
    requires_toolsets:
    - terminal
    provenance: official
---

# Git Workflow
- **Status:** `git status`, `git diff`, `git log --oneline --graph`
- **Branch:** `git switch -c feature/x` ; back to main `git switch main`
- **Commit:** keep small and meaningful; stage in pieces `git add -p`
- **Stay current:** `git fetch` then `git rebase origin/main` (linear history)
- **Conflict:** fix the file -> `git add <file>` -> `git rebase --continue`
- **Undo:** amend last commit `git commit --amend`; revert a change `git revert <sha>`
- **Stash:** `git stash push -m "msg"`, restore `git stash pop`
