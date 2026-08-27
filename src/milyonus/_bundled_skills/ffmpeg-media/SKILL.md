---
name: ffmpeg-media
description: Convert and edit audio/video with ffmpeg
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - ffmpeg
    - video
    - audio
    category: media
    requires_toolsets:
    - terminal
    provenance: official
---

# ffmpeg
- **Convert:** `ffmpeg -i input.mov output.mp4`
- **Extract audio:** `ffmpeg -i video.mp4 -vn audio.mp3`
- **Trim:** `ffmpeg -i x.mp4 -ss 00:00:10 -t 00:00:30 -c copy clip.mp4`
- **Resize:** `ffmpeg -i x.mp4 -vf scale=1280:-2 small.mp4`
- **GIF:** `ffmpeg -i x.mp4 -vf "fps=10,scale=480:-1" out.gif`
- **Info:** `ffprobe file`
