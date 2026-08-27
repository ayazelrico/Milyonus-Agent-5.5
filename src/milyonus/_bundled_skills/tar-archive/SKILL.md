---
name: tar-archive
description: Archiving with tar and compression tools
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - tar
    - archive
    - backup
    category: system
    requires_toolsets:
    - terminal
    provenance: official
---

# tar & compression
- **Create:** `tar -czf archive.tar.gz dir/` (gzip)
- **Extract:** `tar -xzf archive.tar.gz`
- **List:** `tar -tzf archive.tar.gz`
- **zstd (fast):** `tar --zstd -cf archive.tar.zst dir/`
- **Extract one file:** `tar -xzf archive.tar.gz path/file`
- **Exclude:** `tar -czf a.tgz dir --exclude='*.log'`
