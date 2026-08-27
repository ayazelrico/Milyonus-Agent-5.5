"""Trust-as-a-boundary: decay math, auto-demotion, and reaffirmation."""

import time

from milyonus.config.schema import MemoryConfig
from milyonus.memory.consolidate import consolidate
from milyonus.memory.model import Provenance
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.store import MemoryStore
from milyonus.memory.trust import current_trust, half_life_seconds

CFG = MemoryConfig(t1_review_days=180, t2_review_days=60, trust_demote_floor=0.25)


def test_t0_never_decays():
    assert half_life_seconds("T0", CFG) is None
    assert current_trust("T0", None, time.time(), CFG) == 1.0


def test_trust_halves_at_half_life():
    hl = half_life_seconds("T1", CFG)
    now = 1_000_000.0
    # exactly one half-life ago -> ~0.5
    assert abs(current_trust("T1", now - hl, now, CFG) - 0.5) < 1e-6
    # two half-lives -> ~0.25
    assert abs(current_trust("T1", now - 2 * hl, now, CFG) - 0.25) < 1e-6
    # fresh -> 1.0
    assert current_trust("T1", now, now, CFG) == 1.0


def _prov():
    return Provenance(source_kind="user-direct", session_id="s", turn_id=0)


async def test_decayed_memory_demoted_to_quarantine(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    pipe = MemoryPipeline(store, config=CFG)
    mid = store.insert_candidate("user likes dark mode", trust_tier="T1", provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    # backdate last_reaffirmed_at to 3 half-lives ago -> trust ~0.125 < floor 0.25
    hl = half_life_seconds("T1", CFG)
    store._conn.execute(
        "UPDATE memory SET last_reaffirmed_at=? WHERE id=?",
        (time.time() - 3 * hl, mid),
    )
    store._conn.commit()
    report = await consolidate(pipe)
    assert report.demoted == 1
    # policy (a): demoted to quarantine (pending), NOT deleted
    assert store.get(mid).state == "pending"


async def test_reaffirm_prevents_demotion(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    pipe = MemoryPipeline(store, config=CFG)
    mid = store.insert_candidate("user is in Istanbul", trust_tier="T1", provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    hl = half_life_seconds("T1", CFG)
    store._conn.execute(
        "UPDATE memory SET last_reaffirmed_at=? WHERE id=?", (time.time() - 3 * hl, mid)
    )
    store._conn.commit()
    store.reaffirm(mid)  # re-earn trust
    report = await consolidate(pipe)
    assert report.demoted == 0
    assert store.get(mid).state == "active"
    assert store.get(mid).reaffirm_count == 1


async def test_fresh_memory_not_demoted(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    pipe = MemoryPipeline(store, config=CFG)
    mid = store.insert_candidate("recent fact", trust_tier="T1", provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    report = await consolidate(pipe)
    assert report.demoted == 0
    assert store.get(mid).state == "active"


async def test_ledger_records_reaffirm_and_demote(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    mid = store.insert_candidate("x", trust_tier="T1", provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    store.reaffirm(mid)
    actions = [e["action"] for e in store.ledger_entries()]
    assert "reaffirm" in actions
    assert store.verify_ledger() is True
