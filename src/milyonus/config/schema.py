"""Strict configuration schema for Milyonus.

ADR-009: config is validated by a strict schema. Unknown keys are a startup
error, never silently ignored — a typo must fail loud, not misconfigure a
security control. Security-relevant fields are grouped so they are easy to audit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderName = Literal["anthropic", "openai", "local"]


class _Strict(BaseModel):
    # extra="forbid" is the whole point: unknown keys raise instead of passing through.
    model_config = ConfigDict(extra="forbid")


class ProviderConfig(_Strict):
    name: ProviderName = "anthropic"
    model: str = "claude-opus-4-8"
    # A separate, cheap model used only to verify memory-promotion decisions
    # (ADR-003). Isolating it means one poisoned model call is not enough.
    verifier_model: str = "claude-haiku-4-5-20251001"
    base_url: str | None = None
    # Env var that holds the API key. Lets OpenRouter (OPENROUTER_API_KEY) or a
    # custom gateway coexist with the provider name "openai".
    api_key_env: str | None = None
    max_output_tokens: int = 4096


class MemoryConfig(_Strict):
    """Verified-memory pipeline knobs. Defaults are the safe end of each range."""

    # No candidate is ever written straight to durable memory. This cannot be
    # disabled from config — it is the core guarantee, listed here for visibility.
    direct_write: Literal[False] = False
    # T3 (third-party) claims need this many independent confirmations to promote.
    t3_confirmations_required: int = Field(default=2, ge=1, le=5)
    # Unconfirmed T3 claims expire after this many days.
    t3_ttl_days: int = Field(default=14, ge=1)
    # Promotion is a security boundary, not permanent belief: promoted memory
    # decays and must be re-earned. Half-life (days) per tier — trust halves over
    # this span since the last reaffirmation. T0 (operator) never decays.
    t1_review_days: int = Field(default=180, ge=1)  # user-direct
    t2_review_days: int = Field(default=60, ge=1)  # agent-observed
    # Below this trust score an active memory is demoted back to quarantine
    # (re-validatable), so unrenewed trust falls on its own.
    trust_demote_floor: float = Field(default=0.25, ge=0.05, le=0.9)
    # T0 is the operator-authority tier. A staged T0 write requires a SECOND
    # signed `activate` AND at least this many seconds since it was staged
    # (AND-layered review gap). Time-window alone never activates T0.
    t0_review_seconds: int = Field(default=300, ge=0)
    # Cosine similarity above which a new proposal is treated as a possible
    # rephrase of a previously rejected idea (negative-memory check).
    rephrase_similarity: float = Field(default=0.86, ge=0.5, le=0.99)
    # L1 frozen-snapshot character budgets.
    agent_profile_chars: int = Field(default=2200, ge=500)
    user_profile_chars: int = Field(default=1400, ge=500)


class SecurityConfig(_Strict):
    """Fields here gate irreversible/outward actions. Treat changes as sensitive."""

    sandbox_backend: Literal["local", "docker", "ssh", "modal", "daytona"] = "local"
    # Gateway default is deny. Turning this on prints a loud startup warning.
    gateway_allow_all_users: bool = False
    # SSRF protection is always on and cannot be disabled; present for audit only.
    ssrf_protection: Literal[True] = True
    website_blocklist: list[str] = Field(default_factory=list)
    # Extra env var names a skill may pass through to subprocesses. Names matching
    # KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH are always blocked regardless.
    env_passthrough: list[str] = Field(default_factory=list)


class TelemetryConfig(_Strict):
    # Opt-in, off by default (open question #5 — safe default until decided).
    enabled: bool = False


class MilyonusConfig(_Strict):
    """Top-level config, loaded from ~/.milyonus/config.toml."""

    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
