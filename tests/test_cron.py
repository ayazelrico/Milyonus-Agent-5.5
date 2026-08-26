"""Cron store: interval parsing, scheduling, due detection."""

import pytest

from milyonus.cron.store import CronStore, parse_interval


def test_parse_interval():
    assert parse_interval("30m") == 1800
    assert parse_interval("2h") == 7200
    assert parse_interval("1d") == 86400


def test_invalid_interval():
    with pytest.raises(ValueError):
        parse_interval("banana")


def test_add_and_list(tmp_path):
    s = CronStore(tmp_path / "state.db")
    tid = s.add("günlük özet", "1d", "Bugünü özetle")
    tasks = s.list()
    assert len(tasks) == 1 and tasks[0].id == tid


def test_due_detection(tmp_path):
    s = CronStore(tmp_path / "state.db")
    tid = s.add("test", "1h", "yap")
    assert s.due(now=0) == []  # not due yet
    import time

    assert any(t.id == tid for t in s.due(now=time.time() + 4000))


def test_remove(tmp_path):
    s = CronStore(tmp_path / "state.db")
    tid = s.add("x", "1h", "y")
    assert s.remove(tid) is True
    assert s.list() == []
