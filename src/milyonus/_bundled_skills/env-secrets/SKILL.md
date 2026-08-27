---
name: env-secrets
description: Manage environment variables and secrets safely
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - env
    - secret
    category: security
    requires_toolsets:
    - terminal
    provenance: official
---

# Environment Variables & Secrets
- **Set:** `export API_URL=https://...` (session only)
- **.env file:** `KEY=value` lines; never commit, add to `.gitignore`
- **Perms:** `chmod 600` secret files
- **Load (shell):** `set -a; . ./.env; set +a`
- **Never:** hardcode keys, log them, or put them in URL query strings
- **Rotate:** on suspected leak, revoke and regenerate immediately
