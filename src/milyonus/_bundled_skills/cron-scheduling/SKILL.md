---
name: cron-scheduling
description: cron ifadeleriyle zamanlanmış görevler
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - cron
    - zamanlama
    category: sistem
    requires_toolsets:
    - terminal
    provenance: official
---

# Cron Zamanlama
- **Düzenle:** `crontab -e` ; listele `crontab -l`
- **Biçim:** `dakika saat gün ay haftagünü komut`
- **Örnekler:** her saat `0 * * * *` ; her gün 09:00 `0 9 * * *` ; her Pazartesi `0 9 * * 1`
- **Her 15 dk:** `*/15 * * * *`
- Çıktıyı yakala: `... >> /var/log/gorev.log 2>&1`
- İfade doğrula: crontab.guru mantığını kullan (dakika/saat/gün/ay/hafta)
