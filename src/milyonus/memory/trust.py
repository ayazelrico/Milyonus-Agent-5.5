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


def half_life_seconds(tier: TrustTier, config: MemoryConfig) -> float | None:
    """Half-life in seconds for a tier, or None if it never decays."""
    days = {
        "T0": None,
        "T1": config.t1_review_days,
        "T2": config.t2_review_days,
        "T3": config.t3_ttl_days,
        "T4": config.t3_ttl_days,
    }.get(tier)
    return None if days is None else days * _DAY


def current_trust(
    tier: TrustTier, last_reaffirmed_at: float | None, now: float, config: MemoryConfig
) -> float:
    """Trust in [0,1]: 0.5 ** (age / half_life). Non-decaying tiers return 1.0."""
    hl = half_life_seconds(tier, config)
    if hl is None:
        return 1.0
    base = last_reaffirmed_at if last_reaffirmed_at is not None else now
    age = max(0.0, now - base)
    return float(0.5 ** (age / hl))


def review_at(tier: TrustTier, base_time: float, config: MemoryConfig) -> float | None:
    """When the memory becomes due for review (one half-life out)."""
    hl = half_life_seconds(tier, config)
    return None if hl is None else base_time + hl
