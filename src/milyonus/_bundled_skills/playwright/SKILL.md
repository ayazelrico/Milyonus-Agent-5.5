---
name: playwright
description: Playwright ile tarayıcı otomasyonu ve E2E test
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - playwright
    - test
    - browser
    - e2e
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# Playwright (tarayıcı otomasyonu / E2E)

## Kurulum
```bash
pip install playwright && playwright install chromium
# veya JS: npm i -D @playwright/test && npx playwright install
```

## Betik (Python, async)
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto("https://example.com")
    await page.fill("#search", "milyonus")
    await page.click("button[type=submit]")
    await page.wait_for_selector(".result")
    print(await page.title())
    await browser.close()
```

## Seçiciler & aksiyonlar
- **Rol tabanlı (önerilen):** `page.get_by_role("button", name="Gönder")`.
- **Metin/etiket:** `get_by_text`, `get_by_label`, `get_by_placeholder`.
- **Aksiyon:** `click`, `fill`, `type`, `check`, `select_option`, `hover`.
- **Bekleme:** otomatik; `wait_for_selector` / `expect(...).to_be_visible()` ile netleştir.

## Hata ayıklama
```bash
npx playwright test --headed --debug     # görünür + adım adım
npx playwright test --trace on           # trace kaydı → trace.zip
npx playwright show-trace trace.zip
```
- Ekran görüntüsü: `page.screenshot(path="s.png")`; kırıldığında delil olur.
