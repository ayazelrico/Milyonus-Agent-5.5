---
name: systemd-services
description: Manage services and logs with systemd
version: 1.0.0
platforms:
- linux
metadata:
  milyonusagentskill:
    tags:
    - systemd
    - service
    category: system
    requires_toolsets:
    - terminal
    provenance: official
---

# systemd
- **Status:** `systemctl status service`
- **Start/stop:** `systemctl start|stop|restart service`
- **On boot:** `systemctl enable --now service`
- **Logs:** `journalctl -u service -f` (live), `-n 100` last 100 lines
- **Edit unit:** `/etc/systemd/system/name.service` ; then `systemctl daemon-reload`
- **User service:** `systemctl --user ...`
