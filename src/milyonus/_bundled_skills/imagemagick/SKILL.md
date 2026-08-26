---
name: imagemagick
description: ImageMagick ile toplu görüntü işleme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - image
    - magick
    category: medya
    requires_toolsets:
    - terminal
    provenance: official
---

# ImageMagick
- **Dönüştür:** `magick girdi.png cikti.jpg`
- **Boyutlandır:** `magick x.png -resize 800x600 y.png`
- **Toplu:** `for f in *.png; do magick "$f" -resize 50% "kucuk_$f"; done`
- **Kırp:** `magick x.png -crop 200x200+10+10 y.png`
- **Bilgi:** `magick identify x.png`
- **Kalite:** `magick x.png -quality 82 y.jpg`
