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
    # H2: a memory item can be reaffirmed at most once per this many hours — a
    # flood of manipulative messages can't keep resetting the decay clock.
    reaffirm_min_interval_hours: int = Field(default=24, ge=0)
    # H3: a weak (normal user) reaffirm restores trust to a ceiling that drops
    # with repetition after the 3rd; a strong (operator-signed) reaffirm -> 1.0.
    weak_reaffirm_floor: float = Field(default=0.5, ge=0.2, le=1.0)
    # H3: flag an item as anomalous once it has been reaffirmed this many times.
    reaffirm_anomaly_count: int = Field(default=5, ge=2)
    # H4: security/authority-sensitive memory decays faster (half-life * factor).
    sensitive_half_life_factor: float = Field(default=0.25, ge=0.05, le=1.0)
    # H4: if more than this share of demoted memory gets reaffirmed back, the
    # tier's half-life is likely too aggressive (surfaced by `memory stats`).
    false_positive_warn_rate: float = Field(default=0.30, ge=0.05, le=0.9)
    # Cosine similarity above which a new proposal is treated as a possible
    # rephrase of a previously rejected idea (negative-memory check).
    rephrase_similarity: float = Field(default=0.86, ge=0.5, le=0.99)
    # Vector/embedding recall layer. "hashing" is the deps-free default (lexical
    # vector, always on); "openai" uses a real embeddings endpoint; "none" turns
    # semantic recall off and falls back to substring search. Recall is always
    # read-only and trust-weighted (cosine * current_trust), so it can never let
    # a low-trust match outrank a trusted one.
    embedder: Literal["hashing", "openai", "none"] = "hashing"
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = Field(default=256, ge=64, le=4096)
    embed_base_url: str | None = None
    embed_api_key_env: str | None = None
    # How many memories semantic recall returns (after trust re-ranking).
    vector_recall_k: int = Field(default=8, ge=1, le=50)
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


class MCPServerConfig(_Strict):
    """One external MCP (Model Context Protocol) server the agent may connect to.

    Milyonus spawns the server as a stdio/JSON-RPC subprocess, lists its tools,
    and exposes them to the model namespaced as `mcp_<name>_<tool>`. Third-party
    servers are untrusted: the subprocess gets a *filtered* environment (secrets
    are stripped unless named in `env_passthrough`), their output is redacted, and
    their tools default to `caution` risk so the RiskEngine gates side effects.
    """

    name: str = Field(pattern=r"^[a-z0-9_]+$", min_length=1, max_length=40)
    # argv to launch the stdio server, e.g. ["npx","-y","@modelcontextprotocol/server-github"].
    command: list[str] = Field(min_length=1)
    enabled: bool = True
    # Env var names this specific server is allowed to receive. Secret-looking
    # names (KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH) are stripped regardless,
    # so grant a server its key only by naming it here deliberately.
    env_passthrough: list[str] = Field(default_factory=list)
    # Default risk applied to every tool this server exposes. "danger" forces an
    # approval prompt on each call; use it for servers that write or reach out.
    risk: Literal["safe", "caution", "danger"] = "caution"


class MilyonusConfig(_Strict):
    """Top-level config, loaded from ~/.milyonus/config.toml."""

    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    # External MCP servers to connect at startup. Empty by default (opt-in).
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
