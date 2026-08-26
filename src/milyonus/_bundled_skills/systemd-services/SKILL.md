---
name: systemd-services
description: systemd ile servis yönetimi ve loglar
version: 1.0.0
platforms:
- linux
metadata:
  milyonusagentskill:
    tags:
    - systemd
    - service
    category: sistem
    requires_toolsets:
    - terminal
    provenance: official
---

# systemd
- **Durum:** `systemctl status servis`
- **Başlat/durdur:** `systemctl start|stop|restart servis`
- **Açılışta:** `systemctl enable --now servis`
- **Log:** `journalctl -u servis -f` (canlı), `-n 100` son 100 satır
- **Birim düzenle:** `/etc/systemd/system/ad.service` ; sonra `systemctl daemon-reload`
- **Kullanıcı servisi:** `systemctl --user ...`
