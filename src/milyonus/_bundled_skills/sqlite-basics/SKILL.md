---
name: sqlite-basics
description: Query data with the SQLite CLI
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - sqlite
    - sql
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# SQLite
- **Open:** `sqlite3 database.db`
- **Tables:** `.tables` ; schema `.schema table`
- **Query:** `SELECT * FROM t LIMIT 10;`
- **Format:** `.mode column`, `.headers on`
- **Import/export:** `.import data.csv table` / `.output out.csv`
- **Backup:** `.backup backup.db`
