---
name: docker-basics
description: Docker imaj ve konteyner temel işlemleri
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - docker
    - container
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# Docker Temelleri
- **İmajlar:** `docker images`, çek `docker pull nginx:alpine`
- **Çalıştır:** `docker run --rm -it -p 8080:80 nginx:alpine`
- **Konteynerler:** `docker ps -a`, durdur `docker stop <id>`
- **Loglar:** `docker logs -f <id>`
- **İçine gir:** `docker exec -it <id> sh`
- **Temizlik:** `docker system df`, kullanılmayanları temizle `docker image prune`
- **Build:** `docker build -t ad:etiket .`
