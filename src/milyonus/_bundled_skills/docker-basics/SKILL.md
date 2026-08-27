---
name: docker-basics
description: Core Docker image and container operations
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

# Docker Basics
- **Images:** `docker images`, pull `docker pull nginx:alpine`
- **Run:** `docker run --rm -it -p 8080:80 nginx:alpine`
- **Containers:** `docker ps -a`, stop `docker stop <id>`
- **Logs:** `docker logs -f <id>`
- **Exec in:** `docker exec -it <id> sh`
- **Cleanup:** `docker system df`, prune unused `docker image prune`
- **Build:** `docker build -t name:tag .`
