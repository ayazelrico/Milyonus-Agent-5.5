---
name: http-curl
description: Test and debug REST APIs with curl
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
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# HTTP with curl
- **GET:** `curl -s https://api.example.com/x | jq .`
- **Header:** `curl -H "Authorization: Bearer $TOKEN" ...`
- **POST JSON:** `curl -X POST -H "Content-Type: application/json" -d '{"a":1}' url`
- **Status code:** `curl -o /dev/null -w "%{http_code}\n" url`
- **Verbose:** `-v` ; follow redirects `-L` ; timeout `--max-time 10`
- **Upload file:** `curl -F "file=@path" url`
