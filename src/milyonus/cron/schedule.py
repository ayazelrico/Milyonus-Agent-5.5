"""Schedule parsing: intervals, cron expressions, and natural language.

The honest mechanism behind "proactivity" (part 2 of the design note): the LLM is
a compiler from natural language to a structured schedule; a plain scheduler does
the actual triggering. This module is that compiler + a dependency-free 5-field
cron evaluator that computes the next run time.

Accepted specs:
  interval   "30m", "2h", "1d"
  cron       "0 9 * * *"  (minute hour day-of-month month day-of-week)
  natural    "every day at 9:00", "every weekday at 8am", "hourly",
             "every monday at 18:00", "every morning", "every 15 minutes"
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

_UNITS = {"m": 60, "h": 3600, "d": 86400}
_DOW = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}


class ScheduleError(ValueError):
    pass


@dataclass(slots=True)
class Schedule:
    """Either an interval (seconds) or a 5-field cron expression."""

    kind: str  # "interval" | "cron"
    interval_s: int = 0
    cron: str = ""
    display: str = ""

    def next_after(self, now: float) -> float:
        if self.kind == "interval":
            return now + self.interval_s
        return _cron_next(self.cron, now)


# --- interval -----------------------------------------------------------


def parse_interval(spec: str) -> int:
    spec = spec.strip().lower()
    if not spec or spec[-1] not in _UNITS or not spec[:-1].isdigit():
        raise ScheduleError(f"invalid interval: {spec} (e.g. 30m, 2h, 1d)")
    return int(spec[:-1]) * _UNITS[spec[-1]]


# --- cron evaluation ----------------------------------------------------


def _field_matches(field: str, value: int, lo: int, hi: int) -> bool:
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = int(step_s)
        if part in ("*", ""):
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(part)
        if start <= value <= end and (value - start) % step == 0:
            return True
    return False


def _cron_matches(cron: str, dt: datetime) -> bool:
    fields = cron.split()
    if len(fields) != 5:
        raise ScheduleError(f"cron must have 5 fields: {cron!r}")
    minute, hour, dom, month, dow = fields
    # cron day-of-week: 0 or 7 = Sunday. Python weekday(): Mon=0..Sun=6.
    py_dow = (dt.weekday() + 1) % 7  # -> Sun=0..Sat=6
    return (
        _field_matches(minute, dt.minute, 0, 59)
        and _field_matches(hour, dt.hour, 0, 23)
        and _field_matches(dom, dt.day, 1, 31)
        and _field_matches(month, dt.month, 1, 12)
        and (
            _field_matches(dow, py_dow, 0, 6)
            or _field_matches(dow, 7 if py_dow == 0 else py_dow, 0, 7)
        )
    )


def _cron_next(cron: str, now: float) -> float:
    """Next timestamp strictly after `now` that matches the cron expression."""
    dt = datetime.fromtimestamp(now).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(366 * 24 * 60):  # cap: one year of minutes
        if _cron_matches(cron, dt):
            return dt.timestamp()
        dt += timedelta(minutes=1)
    raise ScheduleError(f"no matching time within a year for cron {cron!r}")


# --- natural language ---------------------------------------------------

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)


def _parse_time(text: str, default_h: int = 9, default_m: int = 0) -> tuple[int, int]:
    m = _TIME_RE.search(text)
    if not m:
        return default_h, default_m
    h = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    return h % 24, minute % 60


def _nl_to_cron(text: str) -> str | None:
    t = text.strip().lower()

    if t in ("hourly", "every hour"):
        return "0 * * * *"
    if t in ("daily", "every day", "every morning", "every night", "every evening"):
        h = {"morning": 9, "night": 21, "evening": 20}.get(t.split()[-1], 9)
        return f"0 {h} * * *"

    # "every <weekday> [at HH:MM]"
    for name, dow in _DOW.items():
        if re.search(rf"\bevery\s+{name}\b", t) or re.search(rf"\b{name}s?\b.*\bat\b", t):
            h, mi = _parse_time(t, 9, 0)
            return f"{mi} {h} * * {dow}"

    if "weekday" in t:  # every weekday
        h, mi = _parse_time(t, 9, 0)
        return f"{mi} {h} * * 1-5"

    # "every day at HH:MM" / "at HH:MM" / "daily at HH"
    if "at " in t and ("every day" in t or "daily" in t or t.startswith("at ")):
        h, mi = _parse_time(t)
        return f"{mi} {h} * * *"

    return None


def parse_schedule(spec: str) -> Schedule:
    """Parse an interval, cron expression, or natural-language schedule."""
    spec = spec.strip()

    # 5-field cron?
    if len(spec.split()) == 5 and all(c.isdigit() or c in "*/,-" for c in spec.replace(" ", "")):
        _cron_matches(spec, datetime.now())  # validate
        return Schedule("cron", cron=spec, display=f"cron: {spec}")

    # "every N minutes/hours/days" -> interval
    m = re.match(r"every\s+(\d+)\s*(m|min|minute|h|hour|hr|d|day)s?", spec.lower())
    if m:
        n = int(m.group(1))
        unit = m.group(2)[0]
        return Schedule("interval", interval_s=n * _UNITS[unit], display=f"every {n}{unit}")

    # natural language -> cron
    cron = _nl_to_cron(spec)
    if cron:
        return Schedule("cron", cron=cron, display=spec)

    # bare interval "30m"
    try:
        secs = parse_interval(spec)
        return Schedule("interval", interval_s=secs, display=spec)
    except ScheduleError:
        pass

    raise ScheduleError(
        f"could not parse schedule: {spec!r} (try '30m', '0 9 * * *', or 'every day at 9:00')"
    )
