---
name: sqlite-basics
description: SQLite komut satırı ile veri sorgulama
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - sqlite
    - sql
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# SQLite
- **Aç:** `sqlite3 veritabani.db`
- **Tablolar:** `.tables` ; şema `.schema tablo`
- **Sorgu:** `SELECT * FROM t LIMIT 10;`
- **Biçim:** `.mode column`, `.headers on`
- **İçe/dışa aktar:** `.import veri.csv tablo` / `.output cikti.csv`
- **Yedek:** `.backup yedek.db`
