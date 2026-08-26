---
name: regex-guide
description: Yaygın regex desenleri ve grep/sed kullanımı
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
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# Regex Rehberi
- **Karakter:** `\d` rakam, `\w` kelime, `\s` boşluk, `.` herhangi
- **Nicelik:** `*` 0+, `+` 1+, `?` 0/1, `{2,4}` aralık
- **Sınır:** `^` başı, `$` sonu, `\b` kelime sınırı
- **Grup:** `(abc)` ; alternatif `a|b` ; sınıf `[a-z]`
- **grep:** `grep -E "desen"` (genişletilmiş), `-o` sadece eşleşen
- **sed değiştir:** `sed -E 's/(eski)/[\1]/g' dosya`
- E-posta kaba: `[\w.-]+@[\w.-]+\.\w+`
