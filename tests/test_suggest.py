"""Automation suggestion detects repeated requests (history, not foresight)."""

from milyonus.core.store import SessionStore
from milyonus.proactive.suggest import suggest_automations


def test_recurring_request_suggests_schedule(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    for _i in range(4):
        sid = store.create_session("cli")
        store.append_message(sid, turn=0, role="user",
                             content="every morning send me the sales report")
    sugg = suggest_automations(store, min_count=3, similarity=0.6)
    assert any(s.kind == "schedule" for s in sugg)
    assert sugg[0].count >= 3


def test_repeated_workflow_suggests_skill(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    for _i in range(3):
        sid = store.create_session("cli")
        store.append_message(sid, turn=0, role="user",
                             content="convert this pdf file into a csv table please")
    sugg = suggest_automations(store, min_count=3, similarity=0.5)
    assert any(s.kind == "skill" for s in sugg)


def test_no_suggestion_below_threshold(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    sid = store.create_session("cli")
    store.append_message(sid, turn=0, role="user", content="a one-off unique request here")
    assert suggest_automations(store, min_count=3) == []
