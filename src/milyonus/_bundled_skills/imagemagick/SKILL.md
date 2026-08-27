---
name: imagemagick
description: Batch image processing with ImageMagick
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - image
    - magick
    category: media
    requires_toolsets:
    - terminal
    provenance: official
---

# ImageMagick
- **Convert:** `magick input.png output.jpg`
- **Resize:** `magick x.png -resize 800x600 y.png`
- **Batch:** `for f in *.png; do magick "$f" -resize 50% "small_$f"; done`
- **Crop:** `magick x.png -crop 200x200+10+10 y.png`
- **Info:** `magick identify x.png`
- **Quality:** `magick x.png -quality 82 y.jpg`
