---
name: playwright
description: Browser automation and E2E testing with Playwright
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
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# Playwright (browser automation / E2E)
## Install
```bash
pip install playwright && playwright install chromium
# or JS: npm i -D @playwright/test && npx playwright install
```
## Script (Python, async)
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
## Selectors & actions
- **Role-based (preferred):** `page.get_by_role("button", name="Submit")`.
- **Text/label:** `get_by_text`, `get_by_label`, `get_by_placeholder`.
- **Actions:** `click`, `fill`, `type`, `check`, `select_option`, `hover`.
- **Waiting:** automatic; make it explicit with `wait_for_selector` / `expect(...).to_be_visible()`.
## Debugging
```bash
npx playwright test --headed --debug     # visible + step through
npx playwright test --trace on           # trace recording -> trace.zip
npx playwright show-trace trace.zip
```
- Screenshot: `page.screenshot(path="s.png")`; useful evidence on failure.
