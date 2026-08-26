---
name: postgres-psql
description: psql ile PostgreSQL yönetimi ve sorgulama
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
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# PostgreSQL (psql)
- **Bağlan:** `psql "postgres://kullanici@host:5432/db"`
- **Meta:** `\dt` (tablolar), `\d tablo` (şema), `\l` (veritabanları)
- **Sorgu:** normal SQL; çok satır `;` ile biter
- **Çıktı dosyası:** `\o cikti.txt`
- **Zaman ölç:** `\timing on`
- **CSV dışa aktar:** `\copy (SELECT ...) TO 'x.csv' CSV HEADER`
