---
name: ffmpeg-media
description: ffmpeg ile ses/video dönüştürme ve düzenleme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - ffmpeg
    - video
    - ses
    category: medya
    requires_toolsets:
    - terminal
    provenance: official
---

# ffmpeg
- **Dönüştür:** `ffmpeg -i girdi.mov cikti.mp4`
- **Ses çıkar:** `ffmpeg -i video.mp4 -vn ses.mp3`
- **Kes:** `ffmpeg -i x.mp4 -ss 00:00:10 -t 00:00:30 -c copy kesit.mp4`
- **Yeniden boyutlandır:** `ffmpeg -i x.mp4 -vf scale=1280:-2 kucuk.mp4`
- **GIF:** `ffmpeg -i x.mp4 -vf "fps=10,scale=480:-1" cikti.gif`
- **Bilgi:** `ffprobe dosya`
