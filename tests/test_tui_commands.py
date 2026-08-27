"""TUI slash commands: /model switches provider, /clear, /usage, /exit, /help."""

import io
from dataclasses import dataclass, field

from rich.console import Console

from milyonus.cli.tui import _handle_command
from milyonus.config.schema import MilyonusConfig
from milyonus.core.budget import Budget


@dataclass
class FakeProvider:
    name: str = "anthropic"
    model: str = "claude-opus-4-8"


@dataclass
class FakeLoop:
    provider: FakeProvider = field(default_factory=FakeProvider)
    budget: Budget = field(default_factory=Budget)


def _run(text, loop=None, history=None):
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    loop = loop or FakeLoop()
    history = history if history is not None else [1, 2, 3]
    stop = _handle_command(text, console, loop, MilyonusConfig(), history)
    return stop, buf.getvalue(), loop, history


def test_exit_returns_true():
    stop, _, _, _ = _run("/exit")
    assert stop is True


def test_model_shows_current():
    _, out, _, _ = _run("/model")
    assert "claude-opus-4-8" in out


def test_model_switches():
    _, out, loop, _ = _run("/model claude-sonnet-5")
    assert loop.provider.model == "claude-sonnet-5"
    assert "switched to" in out


def test_clear_empties_history():
    _, out, _, history = _run("/clear")
    assert history == []
    assert "cleared" in out


def test_usage_shows_budget():
    loop = FakeLoop()
    loop.budget.record(input_tokens=100, output_tokens=20)
    _, out, _, _ = _run("/usage", loop=loop)
    assert "tokens 120" in out


def test_help_lists_commands():
    _, out, _, _ = _run("/help")
    assert "/model" in out and "/exit" in out


def test_unknown_command():
    _, out, _, _ = _run("/frobnicate")
    assert "unknown command" in out
