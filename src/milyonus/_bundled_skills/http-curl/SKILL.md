---
name: http-curl
description: curl ile REST API test ve hata ayıklama
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - http
    - curl
    - api
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# curl ile HTTP
- **GET:** `curl -s https://api.example.com/x | jq .`
- **Başlık:** `curl -H "Authorization: Bearer $TOKEN" ...`
- **POST JSON:** `curl -X POST -H "Content-Type: application/json" -d '{"a":1}' url`
- **Durum kodu:** `curl -o /dev/null -w "%{http_code}\n" url`
- **Ayrıntı:** `-v` ; yönlendirme takip `-L` ; zaman aşımı `--max-time 10`
- **Dosya yükle:** `curl -F "file=@yol" url`
