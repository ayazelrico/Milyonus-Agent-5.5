---
name: ripgrep-search
description: Fast code/text search with ripgrep (rg)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - search
    - grep
    - rg
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# ripgrep (rg)
- **Search:** `rg "pattern"` (recursive, respects .gitignore)
- **File type:** `rg "TODO" -t py`
- **Context:** `rg -C 3 "error"` (3 lines before/after)
- **File names only:** `rg -l "import x"`
- **Preview replace:** `rg "old" -l | xargs sed -n 's/old/new/gp'`
- **Hidden files:** `rg --hidden --no-ignore "pattern"`
