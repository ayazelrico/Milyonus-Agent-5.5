---
name: postgres-psql
description: Administer and query PostgreSQL with psql
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - postgres
    - sql
    - psql
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# PostgreSQL (psql)
- **Connect:** `psql "postgres://user@host:5432/db"`
- **Meta:** `\dt` (tables), `\d table` (schema), `\l` (databases)
- **Query:** plain SQL; multi-line ends with `;`
- **Output to file:** `\o out.txt`
- **Time queries:** `\timing on`
- **CSV export:** `\copy (SELECT ...) TO 'x.csv' CSV HEADER`
