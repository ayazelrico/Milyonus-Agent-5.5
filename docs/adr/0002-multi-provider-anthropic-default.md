# ADR-002: Multi-provider, Anthropic default

**Status:** Accepted (2026-08-26)

## Context
Memory-poisoning benchmarks in the literature show the Anthropic (Claude) backend
markedly more resistant than other backends (attack success 0.12–0.20 vs ~1.00).
The vulnerability is architecture × base-model, not architecture alone.

## Decision
Support multiple providers behind one `ProviderRouter`: `anthropic` (default,
Messages API), `openai` (OpenAI-compatible / OpenRouter), and `local`
(Ollama / vLLM). A separate cheap **verifier** model (ADR-003) gates memory
promotion regardless of the main provider.

## Consequences
- Default install steers users toward the most poisoning-resistant backend.
- Local and third-party providers remain first-class but carry a documented
  weaker safety guarantee.
