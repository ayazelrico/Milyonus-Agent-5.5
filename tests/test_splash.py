"""Splash: wordmark alignment and graceful non-tty fallback."""

import io

from rich.console import Console

from milyonus.cli.splash import _wordmark, render_splash


def test_wordmark_is_block_art():
    rows = _wordmark("MILYONUS")
    assert len(rows) == 5
    # every row is block art and the whole thing spans a reasonable banner width
    assert all("█" in r for r in rows)
    assert max(len(r) for r in rows) >= 40


def test_non_tty_fallback_is_plain(monkeypatch):
    # A non-tty stdout must not emit ANSI art — just a clean one-liner.
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    render_splash(console, animate=False, model="anthropic:claude-opus-4-8", session="s1")
    out = buf.getvalue()
    assert "MILYONUS AGENT" in out
    assert "█" not in out  # no block art in the fallback


def test_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    buf = io.StringIO()
    render_splash(Console(file=buf), animate=False, model="m", session="s")
    assert "█" not in buf.getvalue()
