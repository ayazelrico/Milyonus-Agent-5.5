---
name: ssh-remote
description: Remote server operations with SSH and scp/rsync
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - ssh
    - rsync
    - scp
    category: system
    requires_toolsets:
    - terminal
    provenance: official
---

# SSH & File Transfer
- **Connect:** `ssh user@host` ; port `-p 2222`
- **Copy:** `scp file user@host:/path/`
- **Sync (efficient):** `rsync -avz --progress dir/ user@host:/path/`
- **Keys:** `ssh-keygen -t ed25519` ; copy `ssh-copy-id user@host`
- **Tunnel:** `ssh -L 8080:localhost:80 user@host`
- Define `Host` aliases in `~/.ssh/config`
