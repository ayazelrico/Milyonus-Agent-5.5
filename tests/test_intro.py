"""First-run self-introduction: shown once, then marked."""

import io

from rich.console import Console

from milyonus.cli.splash import render_intro
from milyonus.config.paths import is_first_run, mark_introduced


def test_first_run_then_marked(tmp_path, monkeypatch):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    assert is_first_run() is True
    mark_introduced()
    assert is_first_run() is False   # not shown again


def test_intro_mentions_identity_and_help():
    buf = io.StringIO()
    render_intro(Console(file=buf, force_terminal=False))
    out = buf.getvalue()
    assert "Milyonus Agent" in out
    assert "/help" in out
    assert "skills" in out.lower()
