---
name: csv-data
description: Process CSV from the command line (csvkit, awk)
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
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# CSV Processing
- **Preview:** `head -5 data.csv` ; columns `head -1 data.csv | tr ',' '\n'`
- **csvkit:** `csvlook data.csv`, `csvstat data.csv`, `csvcut -c 1,3 data.csv`
- **Filter (csvkit):** `csvgrep -c status -m active data.csv`
- **awk column:** `awk -F, '{print $2}' data.csv`
- **SQL:** `csvsql --query "SELECT ..." data.csv`
- **To JSON:** `csvjson data.csv`
