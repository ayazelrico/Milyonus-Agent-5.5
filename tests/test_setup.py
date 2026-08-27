"""Setup wizard writes a valid, provider-appropriate config incl. model choice."""


from milyonus.config.loader import load_config


def _run(monkeypatch, tmp_path, answers):
    monkeypatch.setenv("MILYONUS_HOME", str(tmp_path))
    it = iter(answers)
    monkeypatch.setattr("milyonus.cli.setup.Prompt.ask", lambda *a, **k: next(it))
    from milyonus.cli.setup import run_setup
    run_setup()
    return load_config(tmp_path / "config.toml")


def test_openai_gets_openai_model_not_claude(monkeypatch, tmp_path):
    # provider, model (default), verifier (default)
    cfg = _run(monkeypatch, tmp_path, ["openai", "gpt-4o", "gpt-4o-mini"])
    assert cfg.provider.name == "openai"
    assert cfg.provider.model == "gpt-4o"          # not claude-opus-4-8 (the bug)
    assert cfg.provider.verifier_model == "gpt-4o-mini"


def test_anthropic_custom_model(monkeypatch, tmp_path):
    cfg = _run(monkeypatch, tmp_path, ["anthropic", "claude-sonnet-5", "claude-haiku-4-5-20251001"])
    assert cfg.provider.name == "anthropic"
    assert cfg.provider.model == "claude-sonnet-5"


def test_openrouter_maps_to_openai_with_base_url(monkeypatch, tmp_path):
    cfg = _run(monkeypatch, tmp_path, ["openrouter", "openai/gpt-4o", "anthropic/claude-haiku-4.5"])
    assert cfg.provider.name == "openai"
    assert "openrouter" in (cfg.provider.base_url or "")
    assert cfg.provider.model == "openai/gpt-4o"


def test_local_needs_no_key(monkeypatch, tmp_path):
    cfg = _run(monkeypatch, tmp_path, ["local", "llama3", "llama3"])
    assert cfg.provider.name == "local"
    assert cfg.provider.model == "llama3"
