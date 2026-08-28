"""Cross-session user model (Honcho-style, made poison-resistant).

Honcho gives an agent a persistent, evolving representation of each user — a
"theory of mind" that survives across sessions and can be *queried* in natural
language. Milyonus keeps that idea but closes its biggest hole: a freely-written,
LLM-inferred user model is a poisoning target. So here the user model is not a
separate trusted store — it is the **verified-memory store, scoped to one user**:

  - Growing it goes through the pipeline. `observe()` *proposes* a candidate; it
    is quarantined and only promoted if it passes verification. Nothing about a
    user is trusted on write, so a manipulative message can't rewrite who the
    user "is".
  - Reading it is trust-ranked and user-scoped. `profile()` and `ask()` see only
    this user's promoted memory (by provenance.actor), so one user's model never
    leaks into another's session — real isolation in a multi-user gateway.
  - It decays. Because it rides the same items, the trust-decay boundary applies:
    a stale claim about the user falls out of the model until reaffirmed.

The result is Honcho's cross-session continuity with Milyonus's verified-memory
guarantees instead of blind trust.
"""

from __future__ import annotations

import re
import time

from milyonus.config.schema import MemoryConfig
from milyonus.memory.model import MemoryItem
from milyonus.memory.store import MemoryStore
from milyonus.memory.trust import current_trust

_TIER_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}

# Heuristic cues that a user message states a *durable* fact about themselves,
# worth proposing as cross-session memory. Deliberately conservative — the
# verifier still gates promotion; this only decides what to *offer*.
_SELF_CUES = (
    r"\bi (?:prefer|like|love|hate|dislike|always|usually|never|want|need|use)\b",
    r"\bmy (?:name|email|timezone|role|job|team|stack|editor|preference)\b",
    r"\bi'?m (?:a|an|based|working|located)\b",
    r"\bi am (?:a|an|based|working|located)\b",
    r"\bcall me\b",
    r"\bben (?:genelde|her zaman|asla)\b",  # TR: I usually / always / never
    r"\b(?:adım|e-?postam|saat dilimim|tercihim)\b",  # TR: my name/email/timezone/preference
)


class UserModel:
    def __init__(
        self,
        store: MemoryStore,
        *,
        user_ref: str,
        config: MemoryConfig | None = None,
        semantic=None,
        pipeline=None,
    ) -> None:
        self.store = store
        self.user_ref = user_ref
        self.config = config or MemoryConfig()
        self.semantic = semantic
        self.pipeline = pipeline

    # --- read: the durable representation -------------------------------

    def facts(self, *, limit: int = 200) -> list[MemoryItem]:
        """This user's promoted memory, highest trust first."""
        items = self.store.active_by_actor(self.user_ref, limit=limit)
        return sorted(items, key=lambda m: (_TIER_RANK.get(m.trust_tier, 9), -m.created_at))

    def _trust(self, m: MemoryItem, now: float) -> float:
        return current_trust(
            m.trust_tier,
            m.last_reaffirmed_at,
            now,
            self.config,
            ceiling=m.trust_ceiling,
            sensitivity=m.sensitivity,
        )

    def profile(self, *, budget: int = 1200) -> str:
        """A compact, trust-ranked digest of the user for the system prompt."""
        now = time.time()
        lines: list[str] = []
        used = 0
        for m in self.facts():
            line = f"[{m.trust_tier} {self._trust(m, now):.2f}] {m.content.strip()}"
            if used + len(line) + 1 > budget:
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(lines)

    def ask(self, query: str, *, k: int | None = None) -> list[tuple[MemoryItem, float]]:
        """Dialectic query: 'what do we know about the user re: X'. Trust-weighted,
        scoped to this user. Uses semantic recall when available, else lexical."""
        if self.semantic is not None and getattr(self.semantic, "enabled", False):
            recalls = self.semantic.recall(query, k=k, actor=self.user_ref)
            if recalls:
                return [(r.item, r.score) for r in recalls]
        now = time.time()
        q = query.casefold()
        hits = [(m, self._trust(m, now)) for m in self.facts() if q in m.content.casefold()]
        hits.sort(key=lambda t: t[1], reverse=True)
        return hits[: (k or self.config.vector_recall_k)]

    def stats(self) -> dict[str, int]:
        facts = self.store.active_by_actor(self.user_ref)
        tiers: dict[str, int] = {}
        for m in facts:
            tiers[m.trust_tier] = tiers.get(m.trust_tier, 0) + 1
        return {"total": len(facts), **tiers}

    # --- write: grow the model through the pipeline ---------------------

    async def observe(self, text: str, *, source_kind: str = "user-direct") -> str:
        """Propose a candidate observation about the user. Returns the resulting
        pipeline state ('active' | 'rejected' | 'pending'). Never a direct write —
        the observation is verified before it can shape the model."""
        if self.pipeline is None:
            raise RuntimeError("UserModel.observe needs a pipeline")
        mid = self.pipeline.propose(
            text.strip(),
            source_kind=source_kind,  # type: ignore[arg-type]
            actor=self.user_ref,
        )
        return await self.pipeline.process_one(mid)

    @staticmethod
    def candidate_observations(user_messages: list[str]) -> list[str]:
        """Heuristically pick user messages that state a durable self-fact worth
        remembering across sessions. Conservative on purpose — the pipeline's
        verifier is the real gate; this just avoids proposing every line."""
        out: list[str] = []
        seen: set[str] = set()
        for msg in user_messages:
            low = msg.casefold().strip()
            if len(low) < 8 or low in seen:
                continue
            if any(re.search(p, low) for p in _SELF_CUES):
                out.append(msg.strip())
                seen.add(low)
        return out

    async def reflect(self, user_messages: list[str]) -> dict[str, int]:
        """Session-end reflection: derive candidate self-facts from this session's
        user messages and propose each through the pipeline. Returns a count of
        outcomes. This is what makes the model grow across sessions — safely,
        because every candidate is verified, not trusted."""
        counts = {"proposed": 0, "active": 0, "rejected": 0, "pending": 0}
        for text in self.candidate_observations(user_messages):
            state = await self.observe(text)
            counts["proposed"] += 1
            counts[state] = counts.get(state, 0) + 1
        return counts
