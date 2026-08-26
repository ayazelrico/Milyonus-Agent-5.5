---
name: git-workflow
description: Git ile dallanma, commit, rebase ve çakışma çözme iş akışı
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

# Git İş Akışı
- **Durum:** `git status`, `git diff`, `git log --oneline --graph`
- **Dal:** `git switch -c ozellik/x` ; ana dala dön `git switch main`
- **Commit:** küçük ve anlamlı tut; `git add -p` ile parça parça sahnele
- **Güncel tut:** `git fetch` sonra `git rebase origin/main` (lineer geçmiş)
- **Çakışma:** dosyayı düzelt → `git add <dosya>` → `git rebase --continue`
- **Geri al:** son commit'i düzenle `git commit --amend`; değişikliği geri al `git revert <sha>`
- **Stash:** `git stash push -m "mesaj"`, geri getir `git stash pop`
