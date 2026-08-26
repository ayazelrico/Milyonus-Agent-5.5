"""Resolve a ProviderConfig into a concrete Provider.

Two provider names cover every backend:
  - "anthropic": Anthropic Messages API (default).
  - "openai":    any OpenAI-compatible endpoint — OpenAI, OpenRouter, local vLLM,
                 or a self-hosted gateway — distinguished by base_url + api_key_env.
The special name "local" is a convenience alias for an OpenAI-compatible server
(Ollama / vLLM) that needs no key.
"""

from __future__ import annotations

from milyonus.config.schema import ProviderConfig
from milyonus.providers.anthropic import AnthropicProvider
from milyonus.providers.base import Provider, ProviderError
from milyonus.providers.openai_compat import (
    OPENROUTER_URL,
    OpenAICompatProvider,
)


def build_provider(cfg: ProviderConfig, *, model: str | None = None) -> Provider:
    """Construct a provider from config. `model` overrides cfg.model (used to
    build the cheaper verifier provider on the same or a different backend)."""
    resolved_model = model or cfg.model
    name = cfg.name

    if name == "anthropic":
        return AnthropicProvider(resolved_model, base_url=cfg.base_url)

    if name == "openai":
        # If base_url points at OpenRouter, default the key env accordingly.
        key_env = cfg.api_key_env
        if key_env is None and cfg.base_url and "openrouter" in cfg.base_url:
            key_env = "OPENROUTER_API_KEY"
        return OpenAICompatProvider(
            resolved_model,
            base_url=cfg.base_url,
            api_key_env=key_env or "OPENAI_API_KEY",
        )

    if name == "local":
        # Local OpenAI-compatible server (Ollama default port). No key required.
        base = cfg.base_url or "http://localhost:11434/v1"
        return OpenAICompatProvider(
            resolved_model, base_url=base, api_key="not-needed", api_key_env="_UNUSED"
        )

    raise ProviderError(f"Bilinmeyen sağlayıcı: {name}")


def openrouter_config(model: str) -> ProviderConfig:
    """Convenience: a ProviderConfig pointed at OpenRouter."""
    return ProviderConfig(
        name="openai",
        model=model,
        base_url=OPENROUTER_URL,
        api_key_env="OPENROUTER_API_KEY",
    )
