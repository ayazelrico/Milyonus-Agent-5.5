"""Browser tool: SSRF guard + graceful 'not installed' path (no live browser)."""

import pytest

from milyonus.tools.browser.tools import make_browser_tools

pytestmark = pytest.mark.asyncio


async def test_ssrf_blocked():
    tool = make_browser_tools()[0]
    out = await tool.handler({"url": "http://169.254.169.254/"})
    assert "SSRF" in out


async def test_localhost_blocked():
    tool = make_browser_tools()[0]
    out = await tool.handler({"url": "http://localhost/"})
    assert "blocked" in out.lower()


async def test_risk_class():
    assert make_browser_tools()[0].risk == "caution"


async def test_missing_playwright_message(monkeypatch):
    # Simulate playwright not installed by making the import fail.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("playwright"):
            raise ImportError("no playwright")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    tool = make_browser_tools()[0]
    out = await tool.handler({"url": "https://example.com/"})
    assert "install" in out.lower()
