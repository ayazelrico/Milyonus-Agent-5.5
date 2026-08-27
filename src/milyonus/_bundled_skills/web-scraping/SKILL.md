---
name: web-scraping
description: 'Ethical web scraping: robots, rate limits, parsing'
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
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# Web Scraping (Ethical)
- **Check first:** `robots.txt` and terms of service; respect rate limits
- **Fetch:** `curl -sL url` or a browser tool (SSRF-guarded)
- **Parse:** Python `selectolax`/`beautifulsoup4` with CSS selectors
- **Wait:** add delay between requests, don't be aggressive
- **Identify:** send a meaningful `User-Agent`
- **Structure:** store output as CSV/JSON; don't hoard raw HTML
- Don't collect or aggregate personal data
