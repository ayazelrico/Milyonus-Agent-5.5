"""Browser automation tool — render JS pages with Playwright (optional dep).

`web_fetch` gets raw HTTP; `browser_fetch` renders the page in a real headless
browser and returns the visible text — for sites that need JavaScript. Every URL
is SSRF-validated before navigation (same fail-closed guard as web_fetch), and
output is redacted. Needs the optional dependency:
    pip install milyonus-agent[browser] && playwright install chromium
"""

from __future__ import annotations

from typing import Any

from milyonus.security.redact import redact
from milyonus.security.ssrf import SSRFBlocked, check_url
from milyonus.tools.registry import Tool

_MAX_TEXT = 200_000


def make_browser_tools() -> list[Tool]:
    async def browser_fetch(args: dict[str, Any]) -> str:
        url = args["url"]
        try:
            check_url(url)
        except SSRFBlocked as exc:
            return f"blocked (SSRF): {exc}"
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return (
                "browser not available — install with: "
                "pip install milyonus-agent[browser] && playwright install chromium"
            )
        wait_selector = args.get("wait_for")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    if wait_selector:
                        await page.wait_for_selector(wait_selector, timeout=15000)
                    text = await page.inner_text("body")
                    title = await page.title()
                    return redact(f"[{title}] {url}\n{text[:_MAX_TEXT]}")
                finally:
                    await browser.close()
        except Exception as exc:  # noqa: BLE001 - surface as a tool result
            return f"browser error: {redact(str(exc))}"

    return [
        Tool(
            name="browser_fetch",
            description=(
                "Render a URL in a headless browser (runs JavaScript) and return "
                "the visible text. Use when web_fetch returns an empty/JS-only page. "
                "SSRF-guarded, read-only."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "wait_for": {"type": "string", "description": "Optional CSS selector to await"},
                },
                "required": ["url"],
            },
            handler=browser_fetch,
            risk="caution",  # reaches the network
        ),
    ]
