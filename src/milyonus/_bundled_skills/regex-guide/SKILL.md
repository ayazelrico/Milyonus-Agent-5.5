---
name: regex-guide
description: Common regex patterns and grep/sed usage
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - regex
    - grep
    - sed
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# Regex Guide
- **Classes:** `\d` digit, `\w` word, `\s` space, `.` any
- **Quantifiers:** `*` 0+, `+` 1+, `?` 0/1, `{2,4}` range
- **Anchors:** `^` start, `$` end, `\b` word boundary
- **Group:** `(abc)` ; alternation `a|b` ; class `[a-z]`
- **grep:** `grep -E "pattern"` (extended), `-o` only the match
- **sed replace:** `sed -E 's/(old)/[\1]/g' file`
- Rough email: `[\w.-]+@[\w.-]+\.\w+`
