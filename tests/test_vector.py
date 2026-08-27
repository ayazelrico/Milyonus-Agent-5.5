"""Vector/embedding memory layer: hashing embedder, persistent index, and
trust-weighted semantic recall."""

import time

from milyonus.config.schema import MemoryConfig
from milyonus.memory.embed import HashingEmbedder, build_embedder
from milyonus.memory.model import Provenance
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.semantic import SemanticMemory
from milyonus.memory.store import MemoryStore
from milyonus.memory.trust import half_life_seconds
from milyonus.memory.vector import VectorIndex

CFG = MemoryConfig(t1_review_days=180, t2_review_days=60)


def _prov():
    return Provenance(source_kind="user-direct", session_id="s", turn_id=0)


# --- embedder ---------------------------------------------------------------


def test_hashing_embedder_deterministic_and_normalized():
    e = HashingEmbedder(dim=128)
    a = e.embed(["the user lives in Istanbul"])[0]
    b = e.embed(["the user lives in Istanbul"])[0]
    assert a == b  # deterministic
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6  # L2-normalized
    assert len(a) == 128


def test_hashing_embedder_overlap_beats_disjoint():
    e = HashingEmbedder(dim=512)
    q = e.embed(["where does the user live city Istanbul"])[0]
    close = e.embed(["the user lives in the city of Istanbul"])[0]
    far = e.embed(["favorite programming language is rust"])[0]

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v, strict=False))

    assert dot(q, close) > dot(q, far)


def test_build_embedder_modes():
    assert build_embedder(MemoryConfig(embedder="none")) is None
    assert isinstance(build_embedder(MemoryConfig(embedder="hashing")), HashingEmbedder)


# --- vector index -----------------------------------------------------------


def test_vector_index_upsert_search_persist(tmp_path):
    db = tmp_path / "state.db"
    idx = VectorIndex(db)
    idx.upsert("a", [1.0, 0.0, 0.0], model="m")
    idx.upsert("b", [0.0, 1.0, 0.0], model="m")
    hits = idx.search([1.0, 0.0, 0.0], model="m", k=2)
    assert hits[0][0] == "a" and hits[0][1] > hits[1][1]
    # allowed_ids filters
    hits2 = idx.search([1.0, 0.0, 0.0], model="m", allowed_ids={"b"})
    assert [h[0] for h in hits2] == ["b"]
    idx.close()
    # persisted across reopen
    idx2 = VectorIndex(db)
    assert idx2.count(model="m") == 2
    idx2.close()


def test_vector_index_isolates_by_model(tmp_path):
    idx = VectorIndex(tmp_path / "s.db")
    idx.upsert("a", [1.0, 0.0], model="hashing-2")
    hits = idx.search([1.0, 0.0], model="openai-x")
    assert hits == []  # different embedder signature -> no cross-comparison


# --- semantic recall --------------------------------------------------------


def _active(store, content, tier="T1"):
    mid = store.insert_candidate(content, trust_tier=tier, provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    return mid


def test_semantic_recall_indexes_on_promotion(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    sem = SemanticMemory(store, config=CFG, embedder=HashingEmbedder(dim=512))
    pipe = MemoryPipeline(store, config=CFG, semantic=sem)
    mid = store.insert_candidate("the user lives in Istanbul", trust_tier="T1", provenance=_prov())
    import asyncio

    asyncio.run(pipe.process_one(mid))
    assert sem.index.count(model=sem.embedder.signature) == 1
    hits = sem.recall("where does the user live")
    assert hits and hits[0].item.id == mid


def test_recall_is_trust_weighted(tmp_path):
    # A decayed T3 that matches the query perfectly must not outrank a fresh T1
    # that matches it well — trust leads, not raw cosine.
    store = MemoryStore(tmp_path / "state.db")
    sem = SemanticMemory(store, config=CFG, embedder=HashingEmbedder(dim=512))

    good = _active(store, "the user prefers dark mode in the editor", tier="T1")
    poison = _active(store, "dark mode editor preference user", tier="T3")
    sem.reindex()

    # Decay the T3 item hard.
    hl = half_life_seconds("T3", CFG)
    store._conn.execute(
        "UPDATE memory SET last_reaffirmed_at=? WHERE id=?",
        (time.time() - 5 * hl, poison),
    )
    store._conn.commit()

    hits = sem.recall("dark mode editor preference")
    top = hits[0]
    assert top.item.id == good
    # the decayed item's trust weight is far below the fresh one's
    poison_hit = next(h for h in hits if h.item.id == poison)
    assert poison_hit.trust < top.trust


def test_recall_excludes_demoted(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    sem = SemanticMemory(store, config=CFG, embedder=HashingEmbedder(dim=256))
    mid = _active(store, "temporary fact about widgets")
    sem.reindex()
    assert sem.recall("widgets")  # recallable while active
    store.demote_to_quarantine(mid, reason="test")
    assert sem.recall("widgets") == []  # no longer active -> not recalled


def test_disabled_embedder_is_noop(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    sem = SemanticMemory(store, config=MemoryConfig(embedder="none"))
    assert sem.enabled is False
    _active(store, "fact")
    assert sem.reindex() == 0
    assert sem.recall("fact") == []
