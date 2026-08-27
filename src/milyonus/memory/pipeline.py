"""The verified-memory pipeline: Ingest -> Quarantine -> Verify -> Promote.

This is the only path from a memory candidate to durable memory (PLAN §4.3).
The agent never writes memory directly; it calls `propose`, which quarantines,
and `process_pending`, which verifies and promotes/rejects according to the
trust-tier rules (PLAN §4.2):

  T0 operator      — set by config, not through this pipeline.
  T1 user-direct   — promote immediately if it passes the injection scan.
  T2 agent-observed— promote with a verifier approval.
  T3 third-party   — needs N confirmations AND verifier approval; else expires.
  T4 subagent/unknown — never auto-promotes; waits for explicit user approval.

Every rejection is written to negative memory so a rephrase is caught next time.
"""

from __future__ import annotations

import time

from milyonus.config.schema import MemoryConfig
from milyonus.memory.model import (
    SOURCE_DEFAULT_TIER,
    Provenance,
    SourceKind,
    TrustTier,
)
from milyonus.memory.negative import is_rephrase
from milyonus.memory.store import MemoryStore
from milyonus.memory.trust import review_at
from milyonus.memory.verifier import RuleBasedVerifier, Verdict


class MemoryPipeline:
    def __init__(
        self,
        store: MemoryStore,
        *,
        config: MemoryConfig | None = None,
        verifier=None,
    ) -> None:
        self.store = store
        self.config = config or MemoryConfig()
        # RuleBasedVerifier is always the floor; a ModelVerifier can be injected.
        self.verifier = verifier or RuleBasedVerifier()

    # --- ingest ---------------------------------------------------------

    def propose(
        self,
        content: str,
        *,
        source_kind: SourceKind,
        source_uri: str | None = None,
        session_id: str | None = None,
        turn_id: int | None = None,
        actor: str | None = None,
        derived_from: str | None = None,
        tier: TrustTier | None = None,
    ) -> str:
        """Quarantine a candidate. Returns the pending item id. Nothing is
        promoted here — promotion happens in process_pending."""
        prov = Provenance(
            source_kind=source_kind,
            source_uri=source_uri,
            session_id=session_id,
            turn_id=turn_id,
            actor=actor,
        )
        resolved_tier = tier or SOURCE_DEFAULT_TIER[source_kind]
        return self.store.insert_candidate(
            content, trust_tier=resolved_tier, provenance=prov, derived_from=derived_from
        )

    # --- verify + promote ----------------------------------------------

    async def _verify(self, content: str, item) -> Verdict:
        existing = [m.content for m in self.store.active()]
        result = self.verifier.verify(
            content,
            source_kind=item.provenance.source_kind,
            trust_tier=item.trust_tier,
            existing=existing,
        )
        # ModelVerifier.verify is async; RuleBasedVerifier.verify is sync.
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def process_one(self, item_id: str) -> str:
        """Evaluate a single pending item. Returns its resulting state."""
        item = self.store.get(item_id)
        if item is None or item.state != "pending":
            return item.state if item else "missing"

        # 1. Rephrase-of-rejected check (negative memory).
        prior_neg = [n["content"] for n in self.store.negatives()]
        rephrase, matched, score = is_rephrase(
            item.content, prior_neg, threshold=self.config.rephrase_similarity
        )
        if rephrase:
            self.store.mark_rejected(
                item_id, reason=f"rephrase of a rejected idea (similarity {score:.2f})"
            )
            return "rejected"

        # 2. Verifier (rule-based floor, optional model on top).
        verdict = await self._verify(item.content, item)
        if not verdict.approved:
            self.store.mark_rejected(item_id, reason=verdict.reason)
            self.store.add_negative(
                item.content, reason=verdict.reason, source_uri=item.provenance.source_uri
            )
            return "rejected"

        # 3. Tier-specific promotion rules.
        tier = item.trust_tier
        if tier == "T1":
            self.store.mark_active(
                item_id,
                verdict=verdict.reason,
                confirmations=1,
                review_at=review_at(tier, time.time(), self.config),
            )
            return "active"
        if tier == "T2":
            self.store.mark_active(
                item_id,
                verdict=verdict.reason,
                confirmations=1,
                review_at=review_at(tier, time.time(), self.config),
            )
            return "active"
        if tier == "T3":
            needed = self.config.t3_confirmations_required
            if item.confirmations + 1 >= needed:
                self.store.mark_active(
                    item_id,
                    verdict=verdict.reason,
                    confirmations=item.confirmations + 1,
                    review_at=review_at(tier, time.time(), self.config),
                )
                return "active"
            # Not enough confirmations yet: keep pending, set an expiry so an
            # unconfirmed third-party claim does not linger forever.
            self.store.add_confirmation(item_id)
            self.store.set_expiry(item_id, expires_at=time.time() + self.config.t3_ttl_days * 86400)
            return "pending"
        # T4 and anything else: never auto-promote.
        return "pending"

    async def process_pending(self) -> dict[str, int]:
        """Process all pending items. Returns a count of resulting states."""
        counts = {"active": 0, "rejected": 0, "pending": 0}
        for item in self.store.by_state("pending"):
            state = await self.process_one(item.id)
            counts[state] = counts.get(state, 0) + 1
        return counts

    def approve_pending(self, item_id: str) -> str:
        """Explicit user approval promotes a pending item regardless of tier
        (the only path for T4). Ledgered as a normal promotion."""
        item = self.store.get(item_id)
        if item is None or item.state != "pending":
            return "missing"
        self.store.mark_active(item_id, verdict="user approval", confirmations=item.confirmations)
        return "active"
