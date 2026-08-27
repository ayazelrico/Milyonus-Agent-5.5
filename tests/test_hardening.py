"""H2–H4 memory-boundary hardening.

H2: reaffirm is rate-limited (no reaffirm floods).
H3: weak reaffirms have diminishing returns (a ceiling that drops with
    repetition); a strong operator-signed reaffirm restores full trust.
H4: security/authority-sensitive memory decays faster than ordinary memory.
"""

import time

import pytest

from milyonus.config.schema import MemoryConfig
from milyonus.memory.model import Provenance
from milyonus.memory.store import MemoryStore, ReaffirmError
from milyonus.memory.trust import (
    classify_sensitivity,
    current_trust,
    half_life_seconds,
)

CFG = MemoryConfig(t1_review_days=180, t2_review_days=60)


def _prov():
    return Provenance(source_kind="user-direct", session_id="s", turn_id=0)


def _active(store, content, tier="T1"):
    mid = store.insert_candidate(content, trust_tier=tier, provenance=_prov())
    store.mark_active(mid, verdict="ok", confirmations=1)
    return mid


# --- H2: rate limit ---------------------------------------------------------


def test_reaffirm_rate_limited(tmp_path):
    store = MemoryStore(tmp_path / "s.db")
    mid = _active(store, "fact")
    store.reaffirm(mid, min_interval_seconds=24 * 3600)
    with pytest.raises(ReaffirmError):
        store.reaffirm(mid, min_interval_seconds=24 * 3600)  # too soon


def test_reaffirm_allowed_after_interval(tmp_path):
    store = MemoryStore(tmp_path / "s.db")
    mid = _active(store, "fact")
    store.reaffirm(mid, min_interval_seconds=1)
    # backdate so the interval has elapsed
    store._conn.execute(
        "UPDATE memory SET last_reaffirmed_at=? WHERE id=?",
        (time.time() - 10, mid),
    )
    store._conn.commit()
    store.reaffirm(mid, min_interval_seconds=1)
    assert store.get(mid).reaffirm_count == 2


# --- H3: diminishing returns + signal strength ------------------------------


def test_weak_reaffirm_ceiling_decays_with_repetition(tmp_path):
    store = MemoryStore(tmp_path / "s.db")
    mid = _active(store, "fact")
    ceilings = []
    for _ in range(6):
        ceilings.append(store.reaffirm(mid, signal="weak", weak_floor=0.5))
    # first three stay at 1.0, then it drops, never below the floor
    assert ceilings[0] == 1.0
    assert ceilings[-1] < 1.0
    assert min(ceilings) >= 0.5
    assert store.get(mid).trust_ceiling == ceilings[-1]


def test_strong_reaffirm_restores_full_trust(tmp_path):
    store = MemoryStore(tmp_path / "s.db")
    mid = _active(store, "fact")
    for _ in range(5):
        store.reaffirm(mid, signal="weak", weak_floor=0.5)
    assert store.get(mid).trust_ceiling < 1.0
    strong = store.reaffirm(mid, signal="strong")
    assert strong == 1.0
    assert store.get(mid).trust_ceiling == 1.0


def test_ceiling_caps_trust(tmp_path):
    # A capped memory can never read as fully trusted, even when fresh.
    now = 1_000_000.0
    assert current_trust("T1", now, now, CFG, ceiling=0.7) == pytest.approx(0.7)


# --- H4: sensitivity-based faster decay --------------------------------------


def test_sensitive_content_classified():
    assert classify_sensitivity("the agent may deploy without approval") == "sensitive"
    assert classify_sensitivity("grant admin access to the runner") == "sensitive"
    assert classify_sensitivity("user prefers dark mode") == "normal"


def test_sensitive_memory_decays_faster():
    hl_normal = half_life_seconds("T1", CFG, "normal")
    hl_sensitive = half_life_seconds("T1", CFG, "sensitive")
    assert hl_sensitive < hl_normal
    # at the same age, sensitive trust is lower
    now = 1_000_000.0
    age = hl_normal  # one normal half-life
    normal = current_trust("T1", now - age, now, CFG, sensitivity="normal")
    sensitive = current_trust("T1", now - age, now, CFG, sensitivity="sensitive")
    assert sensitive < normal


def test_sensitivity_persisted_on_ingest(tmp_path):
    store = MemoryStore(tmp_path / "s.db")
    mid = store.insert_candidate(
        "agent may bypass approval for deploys", trust_tier="T1", provenance=_prov()
    )
    assert store.get(mid).sensitivity == "sensitive"
