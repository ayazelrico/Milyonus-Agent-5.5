---
name: web-scraping
description: 'Etik web kazıma: robots, hız sınırı, ayrıştırma'
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - scrape
    - web
    - html
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# Web Kazıma (Etik)
- **Önce kontrol:** `robots.txt` ve kullanım şartları; hız sınırına uy
- **Getir:** `curl -sL url` ya da tarayıcı aracı (SSRF korumalı)
- **Ayrıştır:** Python `selectolax`/`beautifulsoup4` ile CSS seçici
- **Bekle:** istekler arası gecikme koy, agresif olma
- **Kimliklen:** anlamlı `User-Agent` gönder
- **Yapılandır:** çıktıyı CSV/JSON olarak sakla; ham HTML biriktirme
- Kişisel veriyi toplama/birleştirme
