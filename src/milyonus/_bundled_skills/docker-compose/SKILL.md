---
name: docker-compose
description: Docker Compose ile çok servisli uygulama yönetimi
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
- **Başlat:** `docker compose up -d` (arka planda)
- **Durum/log:** `docker compose ps`, `docker compose logs -f <servis>`
- **Yeniden build:** `docker compose up -d --build`
- **Durdur/temizle:** `docker compose down` (+`-v` volume'ları da siler)
- **Tek servis:** `docker compose restart <servis>`
- compose.yaml'da `depends_on`, `env_file`, `volumes`, `healthcheck` anahtarlarını kullan
