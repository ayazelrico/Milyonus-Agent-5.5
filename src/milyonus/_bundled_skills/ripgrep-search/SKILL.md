---
name: ripgrep-search
description: ripgrep (rg) ile hızlı kod/metin arama
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
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# ripgrep (rg)
- **Ara:** `rg "desen"` (özyinelemeli, .gitignore'a saygılı)
- **Dosya türü:** `rg "TODO" -t py`
- **Bağlam:** `rg -C 3 "hata"` (3 satır önce/sonra)
- **Sadece dosya adı:** `rg -l "import x"`
- **Değiştir (önizleme):** `rg "eski" -l | xargs sed -n 's/eski/yeni/gp'`
- **Gizli dosyalar:** `rg --hidden --no-ignore "desen"`
