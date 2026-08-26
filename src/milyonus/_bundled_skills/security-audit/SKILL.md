---
name: security-audit
description: Bağımlılık, secret ve kod güvenliği denetimi
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - security
    - audit
    - vulnerability
    - sast
    category: guvenlik
    requires_toolsets:
    - terminal
    provenance: official
---

# Güvenlik Denetimi

## Bağımlılık zafiyetleri
```bash
pip-audit                     # Python (PyPI danışmanlıkları)
npm audit --production        # Node
osv-scanner -r .              # çok dilli (Google OSV)
trivy fs .                    # dosya sistemi + imaj taraması
```

## Secret sızıntısı
```bash
gitleaks detect --source .    # commit geçmişinde anahtar ara
trufflehog filesystem .       # doğrulanmış secret'lar
```
- Bulursan: anahtarı **hemen iptal et/yenile**, sonra geçmişten temizle (BFG/filter-repo).

## Statik analiz (SAST)
```bash
bandit -r src/                # Python güvenlik lint'i
semgrep --config auto .       # kural tabanlı, çok dilli
ruff check --select S         # bandit kurallarının bir kısmı
```

## Kontrol listesi (kod incelemesinde)
- Girdi doğrulama; SQL için parametreli sorgu (injection yok).
- Komut çalıştırmada shell=True + kullanıcı girdisi = tehlike.
- SSRF: dış URL'leri özel ağlara karşı doğrula (Milyonus fail-closed yapar).
- Secret'lar env/gizli kasa'da, kodda değil; loglarda redakte.
- En az ayrıcalık; kimlik bilgisi rotasyonu.
- Bağımlılıkları pinle + düzenli güncelle.
