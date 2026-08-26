"""Sleep-time memory consolidation (PLAN §4.7).

A background pass that runs when the agent is idle or on a cron schedule. It does
the housekeeping that keeps verified memory healthy without adding latency to a
live turn:

  - process pending quarantine items (verify + promote/reject),
  - expire due third-party claims,
  - drop exact-duplicate active memories (keep the highest-trust one),
  - flag contradictory pairs for review.

Everything it does is ledgered by the store, so `milyonus audit log` shows what
changed overnight. This is the "learns while it sleeps" behavior, made safe by
the same pipeline that gates live writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from milyonus.memory.negative import jaccard
from milyonus.memory.pipeline import MemoryPipeline

_TIER_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


@dataclass(slots=True)
class ConsolidationReport:
    processed: dict[str, int] = field(default_factory=dict)
    expired: int = 0
    deduped: int = 0
    contradictions: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        p = self.processed
        return (
            f"işlenen: {p.get('active', 0)} aktif / {p.get('rejected', 0)} red / "
            f"{p.get('pending', 0)} bekleyen · süresi dolan: {self.expired} · "
            f"yinelenen: {self.deduped} · çelişki: {len(self.contradictions)}"
        )


async def consolidate(
    pipeline: MemoryPipeline, *, contradiction_threshold: float = 0.9
) -> ConsolidationReport:
    store = pipeline.store
    report = ConsolidationReport()

    # 1. Work through the quarantine.
    report.processed = await pipeline.process_pending()

    # 2. Expire due third-party claims.
    report.expired = len(store.expire_due())

    # 3. Dedupe exact-content active memories (keep highest trust).
    active = store.active()
    by_content: dict[str, list] = {}
    for m in active:
        by_content.setdefault(m.content.strip(), []).append(m)
    for _content, group in by_content.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda m: _TIER_RANK.get(m.trust_tier, 9))
        for dup in group[1:]:
            store.mark_rejected(dup.id, reason="yinelenen bellek birleştirildi")
            report.deduped += 1

    # 4. Flag likely contradictions (very similar content, opposite polarity is
    #    hard to detect lexically, so we surface high-similarity distinct pairs
    #    for human review rather than auto-acting).
    remaining = store.active()
    for i, a in enumerate(remaining):
        for b in remaining[i + 1 :]:
            if a.content == b.content:
                continue
            neg_a = " değil" in a.content or " yok" in a.content
            neg_b = " değil" in b.content or " yok" in b.content
            if neg_a != neg_b and jaccard(a.content, b.content) >= contradiction_threshold:
                report.contradictions.append((a.id, b.id))

    return report
