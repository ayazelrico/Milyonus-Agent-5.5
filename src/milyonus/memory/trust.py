"""Trust decay — promotion grants time-boxed, decaying trust, not permanent belief.

A promoted memory's trust halves every `half-life` since it was last reaffirmed.
When it falls below the demote floor, consolidation returns it to quarantine
(re-validatable) — so trust that is not re-earned falls on its own, rather than a
poisoned or stale memory silently becoming tomorrow's default.

T0 (operator config) never decays; it is authority, not a claim.
"""

from __future__ import annotations

from milyonus.config.schema import MemoryConfig
from milyonus.memory.model import TrustTier

_DAY = 86400.0


def half_life_seconds(
    tier: TrustTier, config: MemoryConfig, sensitivity: str = "normal"
) -> float | None:
    """Half-life in seconds for a tier, or None if it never decays. Security/
    authority-sensitive memory (H4) decays faster by `sensitive_half_life_factor`."""
    days = {
        "T0": None,
        "T1": config.t1_review_days,
        "T2": config.t2_review_days,
        "T3": config.t3_ttl_days,
        "T4": config.t3_ttl_days,
    }.get(tier)
    if days is None:
        return None
    factor = config.sensitive_half_life_factor if sensitivity == "sensitive" else 1.0
    return days * _DAY * factor


def current_trust(
    tier: TrustTier,
    last_reaffirmed_at: float | None,
    now: float,
    config: MemoryConfig,
    *,
    ceiling: float = 1.0,
    sensitivity: str = "normal",
) -> float:
    """Trust in [0,1]: ceiling * 0.5 ** (age / half_life). Non-decaying -> 1.0.
    The ceiling (H3) caps a weakly/often-reaffirmed memory below full trust."""
    hl = half_life_seconds(tier, config, sensitivity)
    if hl is None:
        return 1.0
    base = last_reaffirmed_at if last_reaffirmed_at is not None else now
    age = max(0.0, now - base)
    return float(ceiling * (0.5 ** (age / hl)))


# H4 — sensitivity classification. Security/authority-touching memory decays
# faster: a stale "the agent may act without approval" is far more dangerous than
# a stale "the user likes dark mode".
_SENSITIVE = (
    "approval",
    "approve",
    "permission",
    "permit",
    "access",
    "credential",
    "secret",
    "token",
    "password",
    "delete",
    "deploy",
    "security",
    "admin",
    "authoriz",
    "grant",
    "bypass",
    "disable",
    "override",
    "without confirm",
    "onaysız",
    "yetki",
    "erişim",
    "sil",
    "güvenlik",
    "izin",
)


def classify_sensitivity(content: str) -> str:
    low = content.lower()
    return "sensitive" if any(w in low for w in _SENSITIVE) else "normal"


def review_at(tier: TrustTier, base_time: float, config: MemoryConfig) -> float | None:
    """When the memory becomes due for review (one half-life out)."""
    hl = half_life_seconds(tier, config)
    return None if hl is None else base_time + hl
