"""Version is single-sourced and matches the packaging metadata."""

from importlib.metadata import version

from milyonus import __version__


def test_version_string():
    assert __version__ == "0.1.0.dev0"


def test_version_matches_metadata():
    assert version("milyonus-agent") == __version__
