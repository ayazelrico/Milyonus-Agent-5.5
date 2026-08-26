"""The .env loader reads keys, never overrides the real environment, and never
returns values."""

import os

from milyonus.config import env as envmod


def test_parse_and_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env").write_text('ANTHROPIC_API_KEY="sk-test-123"\n# comment\n')
    applied = envmod.load_env()
    assert applied == ["ANTHROPIC_API_KEY"]  # names only
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-123"


def test_real_env_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=fromfile\n")
    envmod.load_env()
    assert os.environ["ANTHROPIC_API_KEY"] == "real"


def test_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    assert envmod.load_env() == []
    assert envmod.env_file_is_private() is None


def test_permission_detection(tmp_path, monkeypatch):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    p = tmp_path / ".env"
    p.write_text("X=1\n")
    p.chmod(0o600)
    assert envmod.env_file_is_private() is True
    p.chmod(0o644)
    assert envmod.env_file_is_private() is False
