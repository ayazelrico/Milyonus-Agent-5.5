"""Sleep-time consolidation: pending processing, expiry, dedupe, contradiction."""

import pytest

from milyonus.memory.consolidate import consolidate
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.store import MemoryStore

pytestmark = pytest.mark.asyncio


def _pipe(tmp_path):
    return MemoryPipeline(MemoryStore(tmp_path / "state.db"))


async def test_processes_pending(tmp_path):
    p = _pipe(tmp_path)
    p.propose("Kullanıcı sabahçı", source_kind="user-direct")
    report = await consolidate(p)
    assert report.processed.get("active", 0) == 1


async def test_dedupes_active(tmp_path):
    p = _pipe(tmp_path)
    # Two identical active memories at different tiers.
    a = p.store.insert_candidate("aynı içerik", trust_tier="T2", provenance=_prov())
    p.store.mark_active(a, verdict="ok", confirmations=1)
    b = p.store.insert_candidate("aynı içerik", trust_tier="T1", provenance=_prov())
    p.store.mark_active(b, verdict="ok", confirmations=1)
    report = await consolidate(p)
    assert report.deduped == 1
    assert len(p.store.active()) == 1


async def test_contradiction_flagged(tmp_path):
    p = _pipe(tmp_path)
    a = p.store.insert_candidate(
        "kullanıcı toplantı istiyor kesinlikle", trust_tier="T1", provenance=_prov()
    )
    p.store.mark_active(a, verdict="ok", confirmations=1)
    b = p.store.insert_candidate(
        "kullanıcı toplantı istiyor değil kesinlikle", trust_tier="T1", provenance=_prov()
    )
    p.store.mark_active(b, verdict="ok", confirmations=1)
    report = await consolidate(p, contradiction_threshold=0.6)
    assert len(report.contradictions) >= 1


def _prov():
    from milyonus.memory.model import Provenance

    return Provenance(source_kind="user-direct", session_id="s", turn_id=0)
