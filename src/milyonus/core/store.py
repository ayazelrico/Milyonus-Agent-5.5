"""SQLite-backed session store (ADR-006).

One file at ~/.milyonus/state.db holds every session and message, with an FTS5
index over message text for `session.search`. WAL mode keeps reads concurrent
with the agent writing. This is the L3 archive of the memory design — unbounded,
searchable history — distinct from verified memory (L1/L2).

Schema is created on first open and migrated forward by additive statements only.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from milyonus.config.paths import state_db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    channel     TEXT NOT NULL,
    user_ref    TEXT,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    title       TEXT,
    parent_id   TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    turn        INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    tool_json   TEXT,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, turn);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, session_id UNINDEXED, message_id UNINDEXED,
    tokenize = 'unicode61'
);
"""


@dataclass(slots=True)
class SessionRow:
    id: str
    channel: str
    user_ref: str | None
    created_at: float
    updated_at: float
    title: str | None
    parent_id: str | None


def _now() -> float:
    return time.time()


class SessionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_db()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # --- sessions -------------------------------------------------------

    def create_session(
        self,
        channel: str,
        *,
        user_ref: str | None = None,
        parent_id: str | None = None,
        title: str | None = None,
    ) -> str:
        sid = f"s_{uuid.uuid4().hex[:12]}"
        ts = _now()
        with self._tx() as c:
            c.execute(
                "INSERT INTO sessions(id,channel,user_ref,created_at,updated_at,"
                "title,parent_id) VALUES(?,?,?,?,?,?,?)",
                (sid, channel, user_ref, ts, ts, title, parent_id),
            )
        return sid

    def get_session(self, sid: str) -> SessionRow | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        return SessionRow(**dict(row)) if row else None

    def list_sessions(self, *, limit: int = 50) -> list[SessionRow]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [SessionRow(**dict(r)) for r in rows]

    def set_title(self, sid: str, title: str) -> None:
        with self._tx() as c:
            c.execute(
                "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                (title, _now(), sid),
            )

    # --- messages -------------------------------------------------------

    def append_message(
        self,
        session_id: str,
        *,
        turn: int,
        role: str,
        content: str = "",
        tool_payload: dict | None = None,
    ) -> str:
        mid = f"m_{uuid.uuid4().hex[:12]}"
        ts = _now()
        with self._tx() as c:
            c.execute(
                "INSERT INTO messages(id,session_id,turn,role,content,tool_json,"
                "created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    mid,
                    session_id,
                    turn,
                    role,
                    content,
                    json.dumps(tool_payload) if tool_payload else None,
                    ts,
                ),
            )
            if content.strip():
                c.execute(
                    "INSERT INTO messages_fts(content,session_id,message_id) VALUES(?,?,?)",
                    (content, session_id, mid),
                )
            c.execute("UPDATE sessions SET updated_at=? WHERE id=?", (ts, session_id))
        return mid

    def history(self, session_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY turn, created_at",
            (session_id,),
        ).fetchall()

    def search(self, query: str, *, limit: int = 20) -> list[sqlite3.Row]:
        """Full-text search across all message content (L3 session search)."""
        return self._conn.execute(
            "SELECT m.session_id, m.id AS message_id, m.role, "
            "snippet(messages_fts,0,'[',']','…',12) AS snippet, m.created_at "
            "FROM messages_fts f JOIN messages m ON m.id=f.message_id "
            "WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
