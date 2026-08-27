"""Schedule parsing: intervals, cron, and natural language → next run."""

from datetime import datetime

import pytest

from milyonus.cron.schedule import ScheduleError, parse_schedule


def test_interval():
    s = parse_schedule("30m")
    assert s.kind == "interval" and s.interval_s == 1800


def test_every_n_minutes():
    s = parse_schedule("every 15 minutes")
    assert s.kind == "interval" and s.interval_s == 900


def test_cron_expression():
    s = parse_schedule("0 9 * * *")
    assert s.kind == "cron" and s.cron == "0 9 * * *"


def test_nl_daily_at_time():
    s = parse_schedule("every day at 9:00")
    assert s.kind == "cron" and s.cron == "0 9 * * *"


def test_nl_am_pm():
    s = parse_schedule("every day at 8am")
    assert s.cron == "0 8 * * *"
    s2 = parse_schedule("every day at 9pm")
    assert s2.cron == "0 21 * * *"


def test_nl_weekday():
    s = parse_schedule("every monday at 18:00")
    assert s.cron == "0 18 * * 1"


def test_nl_weekdays():
    s = parse_schedule("every weekday at 9")
    assert s.cron == "0 9 * * 1-5"


def test_nl_hourly():
    assert parse_schedule("hourly").cron == "0 * * * *"


def test_nl_morning():
    assert parse_schedule("every morning").cron == "0 9 * * *"


def test_cron_next_computes_future():
    s = parse_schedule("0 9 * * *")
    # from a fixed 08:00, next should be 09:00 the same day
    base = datetime(2026, 1, 1, 8, 0).timestamp()
    nxt = datetime.fromtimestamp(s.next_after(base))
    assert nxt.hour == 9 and nxt.minute == 0


def test_cron_next_rolls_to_tomorrow():
    s = parse_schedule("0 9 * * *")
    base = datetime(2026, 1, 1, 10, 0).timestamp()  # already past 9
    nxt = datetime.fromtimestamp(s.next_after(base))
    assert nxt.day == 2 and nxt.hour == 9


def test_cron_step():
    s = parse_schedule("*/15 * * * *")
    base = datetime(2026, 1, 1, 8, 3).timestamp()
    nxt = datetime.fromtimestamp(s.next_after(base))
    assert nxt.minute == 15


def test_invalid():
    with pytest.raises(ScheduleError):
        parse_schedule("banana o'clock")
