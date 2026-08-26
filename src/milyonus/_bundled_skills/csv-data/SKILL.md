---
name: csv-data
description: Komut satırı araçlarıyla CSV işleme (csvkit, awk)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - csv
    - awk
    - data
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# CSV İşleme
- **Önizle:** `head -5 veri.csv` ; sütunlar `head -1 veri.csv | tr ',' '\n'`
- **csvkit:** `csvlook veri.csv`, `csvstat veri.csv`, `csvcut -c 1,3 veri.csv`
- **Filtre (csvkit):** `csvgrep -c durum -m aktif veri.csv`
- **awk sütun:** `awk -F, '{print $2}' veri.csv`
- **SQL:** `csvsql --query "SELECT ..." veri.csv`
- **JSON'a:** `csvjson veri.csv`
