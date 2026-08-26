"""Tests for the strict config schema — the guarantee that a typo fails loud."""

import pytest

from milyonus.config.loader import ConfigError, load_config
from milyonus.config.schema import MilyonusConfig


def test_defaults_are_valid():
    cfg = MilyonusConfig()
    assert cfg.provider.name == "anthropic"
    assert cfg.memory.direct_write is False  # core guarantee
    assert cfg.security.ssrf_protection is True


def test_unknown_key_rejected(tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text('[provider]\nnaem = "anthropic"\n')  # typo: naem
    with pytest.raises(ConfigError):
        load_config(bad)


def test_direct_write_cannot_be_enabled(tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text("[memory]\ndirect_write = true\n")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_ssrf_cannot_be_disabled(tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text("[security]\nssrf_protection = false\n")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_missing_file_uses_defaults(tmp_path):
    cfg = load_config(tmp_path / "does-not-exist.toml")
    assert isinstance(cfg, MilyonusConfig)


def test_valid_partial_override(tmp_path):
    good = tmp_path / "config.toml"
    good.write_text('[provider]\nmodel = "claude-sonnet-5"\n')
    cfg = load_config(good)
    assert cfg.provider.model == "claude-sonnet-5"
    assert cfg.provider.name == "anthropic"  # default preserved
