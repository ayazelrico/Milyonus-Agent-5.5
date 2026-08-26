---
name: jq-json
description: jq ile JSON sorgulama ve dönüştürme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - json
    - jq
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# jq ile JSON
- **Güzel yazdır:** `jq . dosya.json`
- **Alan seç:** `jq '.data.name'` ; dizi `jq '.items[]'`
- **Filtre:** `jq '.items[] | select(.active==true)'`
- **Dönüştür:** `jq '.items | map({id, name})'`
- **Say:** `jq '.items | length'`
- **Ham çıktı:** `jq -r '.url'` (tırnaksız)
