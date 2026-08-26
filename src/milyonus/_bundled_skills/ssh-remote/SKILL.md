---
name: ssh-remote
description: SSH ve scp/rsync ile uzak sunucu işlemleri
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
    category: sistem
    requires_toolsets:
    - terminal
    provenance: official
---

# SSH & Dosya Aktarımı
- **Bağlan:** `ssh kullanici@host` ; port `-p 2222`
- **Kopyala:** `scp dosya kullanici@host:/yol/`
- **Senkron (verimli):** `rsync -avz --progress dizin/ kullanici@host:/yol/`
- **Anahtar:** `ssh-keygen -t ed25519` ; kopyala `ssh-copy-id kullanici@host`
- **Tünel:** `ssh -L 8080:localhost:80 kullanici@host`
- **Config:** `~/.ssh/config` içinde `Host` takma adları tanımla
