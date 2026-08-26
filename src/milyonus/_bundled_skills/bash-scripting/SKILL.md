---
name: bash-scripting
description: Güvenli bash betik yazımı için desenler
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
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# Bash Betik Yazımı
- **Katı mod:** betik başına `set -euo pipefail`
- **Değişken:** `"$degisken"` her zaman tırnak içinde
- **Koşul:** `if [ -f dosya ]; then ...; fi`
- **Döngü:** `for f in *.txt; do echo "$f"; done`
- **Fonksiyon:** `topla() { echo $(( $1 + $2 )); }`
- **Argüman:** `$1`, `$@`, sayısı `$#`
- **Hata yakala:** `trap 'echo hata satır $LINENO' ERR`
