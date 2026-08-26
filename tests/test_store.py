"""Session store: persistence, history ordering, and FTS5 search."""

from milyonus.core.store import SessionStore


def _store(tmp_path):
    return SessionStore(tmp_path / "state.db")


def test_session_roundtrip(tmp_path):
    s = _store(tmp_path)
    sid = s.create_session("cli", user_ref="me")
    row = s.get_session(sid)
    assert row is not None and row.channel == "cli" and row.user_ref == "me"


def test_history_order(tmp_path):
    s = _store(tmp_path)
    sid = s.create_session("cli")
    s.append_message(sid, turn=0, role="user", content="ilk")
    s.append_message(sid, turn=1, role="assistant", content="ikinci")
    hist = s.history(sid)
    assert [h["content"] for h in hist] == ["ilk", "ikinci"]


def test_fts_search(tmp_path):
    s = _store(tmp_path)
    sid = s.create_session("cli")
    s.append_message(sid, turn=0, role="user", content="Python tip anotasyonu sever")
    s.append_message(sid, turn=1, role="assistant", content="tamam")
    hits = s.search("anotasyonu")
    assert len(hits) == 1
    assert hits[0]["message_id"] is not None


def test_tool_payload_persisted(tmp_path):
    s = _store(tmp_path)
    sid = s.create_session("cli")
    mid = s.append_message(sid, turn=0, role="assistant", tool_payload={"name": "read_file"})
    hist = s.history(sid)
    assert hist[0]["tool_json"] is not None
    assert mid.startswith("m_")


def test_list_sessions_recent_first(tmp_path):
    s = _store(tmp_path)
    a = s.create_session("cli", title="a")
    b = s.create_session("telegram", title="b")
    s.append_message(a, turn=0, role="user", content="bump a")  # touch a's updated_at
    sessions = s.list_sessions()
    assert sessions[0].id == a  # most recently updated
    assert {x.id for x in sessions} == {a, b}
