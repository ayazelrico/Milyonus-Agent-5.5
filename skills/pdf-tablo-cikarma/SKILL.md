---
name: pdf-tablo-cikarma
description: PDF dosyalarından tabloları çıkarır ve CSV'ye çevirir
version: 1.0.0
platforms: [macos, linux]
metadata:
  milyonus:
    tags: [pdf, veri]
    category: veri-isleme
    requires_toolsets: [terminal]
    provenance: user
---

# PDF Tablo Çıkarma

PDF'lerden tablo çıkarmak için:

1. `pdftotext -layout girdi.pdf -` ile ham metni al.
2. Tablo bölgelerini sütun hizasına göre ayır.
3. Sonucu CSV olarak yaz.

Karmaşık tablolar için `camelot-py` veya `tabula-py` kütüphanelerini öner.
