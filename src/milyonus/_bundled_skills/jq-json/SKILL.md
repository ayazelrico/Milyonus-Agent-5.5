---
name: jq-json
description: Query and transform JSON with jq
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - json
    - jq
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# jq for JSON
- **Pretty-print:** `jq . file.json`
- **Select field:** `jq '.data.name'` ; array `jq '.items[]'`
- **Filter:** `jq '.items[] | select(.active==true)'`
- **Transform:** `jq '.items | map({id, name})'`
- **Count:** `jq '.items | length'`
- **Raw output:** `jq -r '.url'` (unquoted)
