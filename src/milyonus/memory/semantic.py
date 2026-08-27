"""Semantic memory — trust-weighted vector recall over durable memory.

This is the join point between the three plain pieces (store, embedder, vector
index). It enforces the two invariants that keep semantic recall from becoming a
new attack surface:

  1. Read-only. Recall never writes, promotes, or elevates. It only ranks memory
     that is already active.
  2. Trust-weighted. The rank is `cosine * current_trust`, not cosine alone. A
     semantically perfect match that lives in a decayed T3 memory can never
     outrank a solid T1 — so an attacker cannot smuggle a poisoned line to the
     top of recall just by wording it to match the query. Trust still leads.

Indexing is driven from promotion (an item is embedded when it becomes active)
and from `milyonus memory reindex` for backfill. If no embedder is configured
(`embedder = "none"`), every method degrades to a no-op and callers fall back to
the lexical path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from milyonus.config.schema import MemoryConfig
from milyonus.memory.embed import Embedder, build_embedder
from milyonus.memory.model import MemoryItem
from milyonus.memory.store import MemoryStore
from milyonus.memory.trust import current_trust
from milyonus.memory.vector import VectorIndex


@dataclass(slots=True)
class Recall:
    item: MemoryItem
    cosine: float
    trust: float

    @property
    def score(self) -> float:
        return self.cosine * self.trust


class SemanticMemory:
    def __init__(
        self,
        store: MemoryStore,
        *,
        config: MemoryConfig | None = None,
        embedder: Embedder | None = None,
        index: VectorIndex | None = None,
    ) -> None:
        self.store = store
        self.config = config or MemoryConfig()
        self.embedder = embedder if embedder is not None else build_embedder(self.config)
        self.index = index or VectorIndex(store.path)

    @property
    def enabled(self) -> bool:
        return self.embedder is not None

    # --- indexing -------------------------------------------------------

    def index_item(self, item: MemoryItem) -> bool:
        """Embed and store one item's vector. Safe to call repeatedly; returns
        False if embeddings are disabled or the embed call failed."""
        if not self.enabled:
            return False
        try:
            vec = self.embedder.embed([item.content])[0]
        except Exception:  # noqa: BLE001 - network/model failure must not break writes
            return False
        self.index.upsert(item.id, vec, model=self.embedder.signature)
        return True

    def reindex(self) -> int:
        """(Re)embed every active memory for the current embedder. Returns the
        number indexed. Used after switching embedders or on first enable."""
        if not self.enabled:
            return 0
        items = self.store.active()
        if not items:
            return 0
        try:
            vectors = self.embedder.embed([m.content for m in items])
        except Exception:  # noqa: BLE001 - degrade cleanly
            return 0
        for item, vec in zip(items, vectors, strict=False):
            self.index.upsert(item.id, vec, model=self.embedder.signature)
        return len(items)

    # --- recall ---------------------------------------------------------

    def recall(self, query: str, *, k: int | None = None) -> list[Recall]:
        """Trust-weighted semantic recall over active memory. Empty list if
        embeddings are disabled (caller falls back to lexical search)."""
        if not self.enabled:
            return []
        k = k or self.config.vector_recall_k
        try:
            qvec = self.embedder.embed([query])[0]
        except Exception:  # noqa: BLE001 - degrade to lexical
            return []
        active = {m.id: m for m in self.store.active()}
        # Over-fetch by cosine, then re-rank by cosine*trust and take top-k.
        hits = self.index.search(
            qvec,
            model=self.embedder.signature,
            k=max(k * 3, k),
            allowed_ids=set(active),
        )
        now = time.time()
        out: list[Recall] = []
        for item_id, cosine in hits:
            if cosine <= 0.0:
                continue
            m = active[item_id]
            trust = current_trust(
                m.trust_tier,
                m.last_reaffirmed_at,
                now,
                self.config,
                ceiling=m.trust_ceiling,
                sensitivity=m.sensitivity,
            )
            out.append(Recall(item=m, cosine=cosine, trust=trust))
        out.sort(key=lambda r: r.score, reverse=True)
        return out[:k]
