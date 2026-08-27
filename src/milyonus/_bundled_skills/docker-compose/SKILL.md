---
name: docker-compose
description: Manage multi-service apps with Docker Compose
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - docker
    - compose
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# Docker Compose
- **Start:** `docker compose up -d` (detached)
- **Status/logs:** `docker compose ps`, `docker compose logs -f <service>`
- **Rebuild:** `docker compose up -d --build`
- **Stop/clean:** `docker compose down` (+`-v` also removes volumes)
- **Single service:** `docker compose restart <service>`
- In compose.yaml use `depends_on`, `env_file`, `volumes`, `healthcheck`
