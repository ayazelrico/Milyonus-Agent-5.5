"""DM pairing: code format, expiry, lockout, rate limit, default-deny."""

import time

from milyonus.gateway.pairing import PairingManager, generate_code


def _mgr(tmp_path):
    return PairingManager(tmp_path / "pairing.json")


def test_code_format():
    code = generate_code()
    assert len(code) == 8
    assert all(c not in "01OIL" for c in code)  # unambiguous alphabet


def test_default_deny(tmp_path):
    m = _mgr(tmp_path)
    assert not m.is_paired("telegram", "user1")


def test_pair_success(tmp_path):
    m = _mgr(tmp_path)
    code = m.new_code("telegram")
    ok, _ = m.redeem("telegram", "user1", code)
    assert ok
    assert m.is_paired("telegram", "user1")


def test_wrong_code_fails(tmp_path):
    m = _mgr(tmp_path)
    m.new_code("telegram")
    ok, _ = m.redeem("telegram", "user1", "WRONGXYZ")
    assert not ok
    assert not m.is_paired("telegram", "user1")


def test_lockout_after_failures(tmp_path):
    m = _mgr(tmp_path)
    for _ in range(5):
        m.redeem("telegram", "u", "BADCODE1")
    ok, msg = m.redeem("telegram", "u", "BADCODE1")
    assert not ok
    assert "locked" in msg


def test_code_wrong_channel(tmp_path):
    m = _mgr(tmp_path)
    code = m.new_code("telegram")
    ok, _ = m.redeem("whatsapp", "u", code)  # code was for telegram
    assert not ok


def test_rate_limit(tmp_path):
    m = _mgr(tmp_path)
    assert m.can_request("telegram", "u")
    m.mark_request("telegram", "u")
    assert not m.can_request("telegram", "u")


def test_persistence_and_perms(tmp_path):
    m = _mgr(tmp_path)
    code = m.new_code("telegram")
    m.redeem("telegram", "user1", code)
    # Reload from disk.
    m2 = PairingManager(tmp_path / "pairing.json")
    assert m2.is_paired("telegram", "user1")
    import stat

    mode = stat.S_IMODE((tmp_path / "pairing.json").stat().st_mode)
    assert mode == 0o600


def test_expired_code(tmp_path, monkeypatch):
    m = _mgr(tmp_path)
    code = m.new_code("telegram")
    # Fast-forward time beyond TTL.
    real = time.time()
    monkeypatch.setattr("milyonus.gateway.pairing.time.time", lambda: real + 4000)
    ok, msg = m.redeem("telegram", "u", code)
    assert not ok
    assert "expired" in msg or "invalid" in msg
