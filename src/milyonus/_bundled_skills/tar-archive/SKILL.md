---
name: tar-archive
description: tar ve sıkıştırma araçlarıyla arşivleme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - tar
    - arşiv
    - backup
    category: sistem
    requires_toolsets:
    - terminal
    provenance: official
---

# tar & sıkıştırma
- **Oluştur:** `tar -czf arsiv.tar.gz dizin/` (gzip)
- **Aç:** `tar -xzf arsiv.tar.gz`
- **Listele:** `tar -tzf arsiv.tar.gz`
- **zstd (hızlı):** `tar --zstd -cf arsiv.tar.zst dizin/`
- **Belirli dosya çıkar:** `tar -xzf arsiv.tar.gz yol/dosya`
- **Hariç tut:** `tar -czf a.tgz dizin --exclude='*.log'`
