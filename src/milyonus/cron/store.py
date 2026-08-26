"""Scheduled tasks storage (PLAN §3.8).

Cron tasks are first-class agent tasks, not just shell jobs: each stores a prompt
that is run through the agent loop on schedule. Stored in state.db.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from milyonus.config.paths import state_db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cron_tasks (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    schedule    TEXT NOT NULL,     -- simple interval spec, e.g. "1h", "30m", "1d"
    prompt      TEXT NOT NULL,
    channel     TEXT,
    user_ref    TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1,
    last_run    REAL,
    next_run    REAL,
    created_at  REAL NOT NULL
);
"""

_UNITS = {"m": 60, "h": 3600, "d": 86400}


def parse_interval(spec: str) -> int:
    """Parse "30m"/"2h"/"1d" into seconds."""
    spec = spec.strip().lower()
    if not spec or spec[-1] not in _UNITS:
        raise ValueError(f"invalid interval: {spec} (e.g. 30m, 2h, 1d)")
    return int(spec[:-1]) * _UNITS[spec[-1]]


@dataclass(slots=True)
class CronTask:
    id: str
    name: str
    schedule: str
    prompt: str
    channel: str | None
    user_ref: str | None
    enabled: bool
    last_run: float | None
    next_run: float | None
    created_at: float


class CronStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_db()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def add(self, name: str, schedule: str, prompt: str, *, channel=None, user_ref=None) -> str:
        interval = parse_interval(schedule)
        tid = f"cron_{uuid.uuid4().hex[:10]}"
        now = time.time()
        self._conn.execute(
            "INSERT INTO cron_tasks(id,name,schedule,prompt,channel,user_ref,"
            "enabled,next_run,created_at) VALUES(?,?,?,?,?,?,1,?,?)",
            (tid, name, schedule, prompt, channel, user_ref, now + interval, now),
        )
        self._conn.commit()
        return tid

    def list(self) -> list[CronTask]:
        rows = self._conn.execute("SELECT * FROM cron_tasks ORDER BY created_at DESC").fetchall()
        return [
            CronTask(
                id=r["id"],
                name=r["name"],
                schedule=r["schedule"],
                prompt=r["prompt"],
                channel=r["channel"],
                user_ref=r["user_ref"],
                enabled=bool(r["enabled"]),
                last_run=r["last_run"],
                next_run=r["next_run"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def remove(self, task_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM cron_tasks WHERE id=?", (task_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def due(self, now: float | None = None) -> list[CronTask]:
        now = now or time.time()
        return [t for t in self.list() if t.enabled and t.next_run and t.next_run <= now]

    def mark_ran(self, task_id: str) -> None:
        task = next((t for t in self.list() if t.id == task_id), None)
        if task is None:
            return
        now = time.time()
        nxt = now + parse_interval(task.schedule)
        self._conn.execute(
            "UPDATE cron_tasks SET last_run=?, next_run=? WHERE id=?", (now, nxt, task_id)
        )
        self._conn.commit()
