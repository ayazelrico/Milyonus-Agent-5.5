---
name: bash-scripting
description: Patterns for safe bash scripting
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - bash
    - shell
    - script
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# Bash Scripting
- **Strict mode:** `set -euo pipefail` at the top
- **Variables:** always quote `"$var"`
- **Condition:** `if [ -f file ]; then ...; fi`
- **Loop:** `for f in *.txt; do echo "$f"; done`
- **Function:** `add() { echo $(( $1 + $2 )); }`
- **Args:** `$1`, `$@`, count `$#`
- **Trap errors:** `trap 'echo error at line $LINENO' ERR`
