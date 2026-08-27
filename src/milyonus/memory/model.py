"""Core value types for the verified-memory system (PLAN §4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Trust tiers (PLAN §4.2). Higher tier = stronger claim to promotion.
TrustTier = Literal["T0", "T1", "T2", "T3", "T4"]

# Where a candidate came from — drives which tier is even allowed.
SourceKind = Literal[
    "operator",  # config.toml (T0)
    "user-direct",  # paired user's own words in DM/CLI (T1)
    "agent-observed",  # agent's first-hand deterministic observation (T2)
    "third-party",  # web / email / document / group chat (T3)
    "subagent",  # child agent summary (T4)
    "unknown",  # anything else (T4)
]

# Lifecycle state of a memory row.
MemoryState = Literal["pending", "active", "rejected", "revoked", "expired", "superseded"]


@dataclass(slots=True)
class Provenance:
    """The sealed record of where a memory came from (PLAN §4.3)."""

    source_kind: SourceKind
    source_uri: str | None = None
    session_id: str | None = None
    turn_id: int | None = None
    actor: str | None = None  # who asserted it (user ref, tool name, subagent id)


@dataclass(slots=True)
class MemoryItem:
    id: str
    content: str
    trust_tier: TrustTier
    state: MemoryState
    provenance: Provenance
    evidence_hash: str
    created_at: float
    verified_at: float | None = None
    verdict: str | None = None  # verifier's short verdict string
    confirmations: int = 0
    expires_at: float | None = None
    superseded_by: str | None = None
    # Trust-as-a-boundary (decays since last reaffirmation).
    trust_score: float = 1.0
    last_reaffirmed_at: float | None = None
    review_at: float | None = None
    reaffirm_count: int = 0


# Default tier for each source kind (PLAN §4.2).
SOURCE_DEFAULT_TIER: dict[SourceKind, TrustTier] = {
    "operator": "T0",
    "user-direct": "T1",
    "agent-observed": "T2",
    "third-party": "T3",
    "subagent": "T4",
    "unknown": "T4",
}
