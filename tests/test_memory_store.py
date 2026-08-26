"""Memory store: no-direct-write, ledger integrity, and cascade revocation."""

from milyonus.memory.model import Provenance
from milyonus.memory.store import MemoryStore


def _store(tmp_path):
    return MemoryStore(tmp_path / "state.db")


def _prov(kind="user-direct", uri=None):
    return Provenance(source_kind=kind, source_uri=uri, session_id="s1", turn_id=0)


def test_candidate_enters_pending_not_active(tmp_path):
    s = _store(tmp_path)
    mid = s.insert_candidate("x", trust_tier="T1", provenance=_prov())
    item = s.get(mid)
    assert item.state == "pending"  # never active on insert
    assert s.active() == []


def test_promote_via_mark_active(tmp_path):
    s = _store(tmp_path)
    mid = s.insert_candidate("x", trust_tier="T1", provenance=_prov())
    s.mark_active(mid, verdict="ok", confirmations=1)
    assert s.get(mid).state == "active"
    assert len(s.active()) == 1


def test_ledger_records_ingest_and_promote(tmp_path):
    s = _store(tmp_path)
    mid = s.insert_candidate("x", trust_tier="T1", provenance=_prov())
    s.mark_active(mid, verdict="ok", confirmations=1)
    actions = [e["action"] for e in s.ledger_entries()]
    assert "ingest" in actions and "promote" in actions
    assert s.verify_ledger() is True


def test_ledger_detects_tampering(tmp_path):
    s = _store(tmp_path)
    mid = s.insert_candidate("x", trust_tier="T1", provenance=_prov())
    s.mark_active(mid, verdict="ok", confirmations=1)
    # Tamper: flip content of a ledger entry directly.
    s._conn.execute("UPDATE memory_ledger SET detail='{\"evil\":1}' WHERE seq=1")
    s._conn.commit()
    assert s.verify_ledger() is False


def test_cascade_revocation(tmp_path):
    s = _store(tmp_path)
    root = s.insert_candidate(
        "kaynaktan olgu", trust_tier="T3", provenance=_prov("third-party", "http://bad")
    )
    s.mark_active(root, verdict="ok", confirmations=2)
    child = s.insert_candidate(
        "türev olgu",
        trust_tier="T3",
        provenance=_prov("agent-observed"),
        derived_from=root,
    )
    s.mark_active(child, verdict="ok", confirmations=1)
    revoked = s.revoke_by_source("http://bad")
    assert set(revoked) == {root, child}  # child cascaded
    assert s.get(root).state == "revoked"
    assert s.get(child).state == "revoked"


def test_negative_memory(tmp_path):
    s = _store(tmp_path)
    s.add_negative("kötü fikir", reason="user rejected", source_uri=None)
    assert len(s.negatives()) == 1


def test_expiry(tmp_path):
    s = _store(tmp_path)
    mid = s.insert_candidate("x", trust_tier="T3", provenance=_prov("third-party"))
    s.mark_active(mid, verdict="ok", confirmations=2)
    s.set_expiry(mid, expires_at=1000.0)
    expired = s.expire_due(now=2000.0)
    assert mid in expired
    assert s.get(mid).state == "expired"
