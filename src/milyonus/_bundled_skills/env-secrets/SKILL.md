---
name: env-secrets
description: Ortam değişkenleri ve gizli anahtarları güvenli yönetme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - env
    - secret
    category: guvenlik
    requires_toolsets:
    - terminal
    provenance: official
---

# Ortam Değişkenleri & Secret'lar
- **Ayarla:** `export API_URL=https://...` (oturumluk)
- **.env dosyası:** `KEY=deger` satırları; koda commit etme, `.gitignore`'a ekle
- **İzin:** secret dosyalarını `chmod 600` yap
- **Yükle (shell):** `set -a; . ./.env; set +a`
- **Asla:** anahtarları koda gömme, log'a yazma, URL query'sine koyma
- **Döndür:** sızıntı şüphesinde anahtarı hemen iptal edip yenile
