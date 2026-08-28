"""SQLite storage for verified memory + hash-chained ledger + negative memory.

Three tables in ~/.milyonus/state.db:
  memory          — every candidate and durable item, with provenance and state.
  memory_ledger   — append-only, hash-chained audit of every state transition
                    (PLAN §6 layer 7). Tampering breaks the chain, detectable by
                    `milyonus audit verify`.
  negative_memory — rejected/failed ideas, so a rephrase can be caught (PLAN §4.4).

Critically, there is NO method that writes a row directly into state="active".
Promotion only happens via the pipeline, which the ledger records. This is the
"no direct write" guarantee expressed in code (PLAN §4.3).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

from milyonus.config.paths import state_db
from milyonus.memory.model import (
    MemoryItem,
    MemoryState,
    Provenance,
    SourceKind,
    TrustTier,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id            TEXT PRIMARY KEY,
    content       TEXT NOT NULL,
    trust_tier    TEXT NOT NULL,
    state         TEXT NOT NULL,
    source_kind   TEXT NOT NULL,
    source_uri    TEXT,
    session_id    TEXT,
    turn_id       INTEGER,
    actor         TEXT,
    evidence_hash TEXT NOT NULL,
    created_at    REAL NOT NULL,
    verified_at   REAL,
    verdict       TEXT,
    confirmations INTEGER NOT NULL DEFAULT 0,
    expires_at    REAL,
    superseded_by TEXT,
    derived_from  TEXT,
    trust_score   REAL NOT NULL DEFAULT 1.0,
    last_reaffirmed_at REAL,
    review_at     REAL,
    reaffirm_count INTEGER NOT NULL DEFAULT 0,
    signature      TEXT,
    key_fingerprint TEXT,
    trust_ceiling  REAL NOT NULL DEFAULT 1.0,
    sensitivity    TEXT NOT NULL DEFAULT 'normal'
);
CREATE INDEX IF NOT EXISTS idx_memory_state ON memory(state);
CREATE INDEX IF NOT EXISTS idx_memory_source ON memory(source_uri);

CREATE TABLE IF NOT EXISTS memory_ledger (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_hash  TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    action     TEXT NOT NULL,
    item_id    TEXT,
    detail     TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS negative_memory (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    reason     TEXT NOT NULL,
    source_uri TEXT,
    created_at REAL NOT NULL
);
"""

_GENESIS = "0" * 64


class ReaffirmError(Exception):
    """Raised when a reaffirm is rejected (e.g. rate-limited)."""


def _now() -> float:
    return time.time()


def evidence_hash(content: str, provenance: Provenance) -> str:
    """Stable hash binding content to its origin — the tamper-evident anchor."""
    payload = json.dumps(
        {
            "content": content,
            "source_kind": provenance.source_kind,
            "source_uri": provenance.source_uri,
            "session_id": provenance.session_id,
            "turn_id": provenance.turn_id,
            "actor": provenance.actor,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MemoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_db()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _migrate(self) -> None:
        """Add trust-boundary columns to pre-existing memory tables (idempotent)."""
        existing = {r[1] for r in self._conn.execute("PRAGMA table_info(memory)")}
        for col, ddl in (
            ("trust_score", "REAL NOT NULL DEFAULT 1.0"),
            ("last_reaffirmed_at", "REAL"),
            ("review_at", "REAL"),
            ("reaffirm_count", "INTEGER NOT NULL DEFAULT 0"),
            ("signature", "TEXT"),
            ("key_fingerprint", "TEXT"),
            ("trust_ceiling", "REAL NOT NULL DEFAULT 1.0"),
            ("sensitivity", "TEXT NOT NULL DEFAULT 'normal'"),
        ):
            if col not in existing:
                self._conn.execute(f"ALTER TABLE memory ADD COLUMN {col} {ddl}")

    # --- ledger ---------------------------------------------------------

    def _ledger_head(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM memory_ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row["entry_hash"] if row else _GENESIS

    def _ledger_append(self, action: str, item_id: str | None, detail: dict) -> None:
        prev = self._ledger_head()
        ts = _now()
        body = json.dumps(
            {"action": action, "item_id": item_id, "detail": detail, "ts": ts},
            sort_keys=True,
            ensure_ascii=False,
        )
        entry = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
        self._conn.execute(
            "INSERT INTO memory_ledger(prev_hash,entry_hash,action,item_id,detail,"
            "created_at) VALUES(?,?,?,?,?,?)",
            (prev, entry, action, item_id, json.dumps(detail, ensure_ascii=False), ts),
        )

    def verify_ledger(self) -> bool:
        """Recompute the whole chain; True if intact (PLAN §6 layer 7)."""
        prev = _GENESIS
        for row in self._conn.execute("SELECT * FROM memory_ledger ORDER BY seq ASC"):
            body = json.dumps(
                {
                    "action": row["action"],
                    "item_id": row["item_id"],
                    "detail": json.loads(row["detail"]) if row["detail"] else {},
                    "ts": row["created_at"],
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            expected = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
            if row["prev_hash"] != prev or row["entry_hash"] != expected:
                return False
            prev = row["entry_hash"]
        return True

    def ledger_entries(self, *, limit: int = 100) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM memory_ledger ORDER BY seq DESC LIMIT ?", (limit,)
        ).fetchall()

    # --- candidate insertion (always pending; never active) -------------

    def insert_candidate(
        self,
        content: str,
        *,
        trust_tier: TrustTier,
        provenance: Provenance,
        derived_from: str | None = None,
    ) -> str:
        """Insert a candidate in state='pending'. This is the ONLY insertion
        path; nothing enters as 'active' (no direct write guarantee)."""
        from milyonus.memory.trust import classify_sensitivity

        mid = f"mem_{uuid.uuid4().hex[:12]}"
        eh = evidence_hash(content, provenance)
        sensitivity = classify_sensitivity(content)
        self._conn.execute(
            "INSERT INTO memory(id,content,trust_tier,state,source_kind,source_uri,"
            "session_id,turn_id,actor,evidence_hash,created_at,derived_from,sensitivity) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid,
                content,
                trust_tier,
                "pending",
                provenance.source_kind,
                provenance.source_uri,
                provenance.session_id,
                provenance.turn_id,
                provenance.actor,
                eh,
                _now(),
                derived_from,
                sensitivity,
            ),
        )
        self._ledger_append(
            "ingest", mid, {"tier": trust_tier, "eh": eh, "sensitivity": sensitivity}
        )
        self._conn.commit()
        return mid

    # --- state transitions (each ledgered) ------------------------------

    def _set_state(self, item_id: str, state: MemoryState, action: str, detail: dict) -> None:
        self._conn.execute("UPDATE memory SET state=? WHERE id=?", (state, item_id))
        self._ledger_append(action, item_id, detail)

    def mark_active(
        self,
        item_id: str,
        *,
        verdict: str,
        confirmations: int,
        review_at: float | None = None,
    ) -> None:
        now = _now()
        self._conn.execute(
            "UPDATE memory SET state='active', verified_at=?, verdict=?, "
            "confirmations=?, trust_score=1.0, trust_ceiling=1.0, last_reaffirmed_at=?, "
            "review_at=? WHERE id=?",
            (now, verdict, confirmations, now, review_at, item_id),
        )
        self._ledger_append(
            "promote", item_id, {"verdict": verdict, "confirmations": confirmations}
        )
        self._conn.commit()

    def reaffirm(
        self,
        item_id: str,
        *,
        review_at: float | None = None,
        min_interval_seconds: float = 0.0,
        signal: str = "weak",
        weak_floor: float = 0.5,
    ) -> float:
        """Re-earn trust — an explicit, rate-limited human action (H2/H3).

        A weak (normal user) reaffirm restores trust to a ceiling that drops with
        repetition after the 3rd, so a patient attacker can't keep an item at full
        trust forever. A strong (operator-signed) reaffirm restores 1.0. Rejects a
        reaffirm inside `min_interval_seconds` of the previous one. Returns the
        applied ceiling."""
        item = self.get(item_id)
        if item is None:
            raise ReaffirmError(f"no such memory: {item_id}")
        now = _now()
        # Rate-limit only against a *previous reaffirm*, not the promotion
        # timestamp (mark_active also sets last_reaffirmed_at).
        if (
            item.reaffirm_count > 0
            and item.last_reaffirmed_at is not None
            and (now - item.last_reaffirmed_at) < min_interval_seconds
        ):
            wait_h = (min_interval_seconds - (now - item.last_reaffirmed_at)) / 3600
            raise ReaffirmError(
                f"reaffirmed too recently — try again in {wait_h:.1f}h "
                "(rate limit prevents reaffirm floods)"
            )
        new_count = item.reaffirm_count + 1
        # Strong (operator-signed) restores full trust; weak reaffirms have
        # diminishing returns after the 3rd, never falling below the floor.
        ceiling = 1.0 if signal == "strong" else max(weak_floor, 1.0 - 0.1 * max(0, new_count - 3))
        interval = (now - item.last_reaffirmed_at) if item.last_reaffirmed_at else None
        self._conn.execute(
            "UPDATE memory SET trust_score=?, trust_ceiling=?, last_reaffirmed_at=?, "
            "review_at=?, reaffirm_count=? WHERE id=?",
            (ceiling, ceiling, now, review_at, new_count, item_id),
        )
        self._ledger_append(
            "reaffirm",
            item_id,
            {
                "signal": signal,
                "ceiling": round(ceiling, 3),
                "count": new_count,
                "interval_s": round(interval) if interval else None,
            },
        )
        self._conn.commit()
        return ceiling

    def demote_to_quarantine(self, item_id: str, *, reason: str) -> None:
        """Return an active memory to quarantine (re-validatable), not deleted."""
        self._set_state(item_id, "pending", "demote", {"reason": reason})
        self._conn.commit()

    def stage_t0(self, content: str, *, signature: str, key_fingerprint: str) -> str:
        """Insert a signed operator (T0) claim in the staged state (passive —
        not yet a default). Activation requires a second signature (see t0.py)."""
        from milyonus.memory.model import Provenance

        prov = Provenance(source_kind="operator", actor="operator")
        mid = f"mem_{uuid.uuid4().hex[:12]}"
        eh = evidence_hash(content, prov)
        now = _now()
        self._conn.execute(
            "INSERT INTO memory(id,content,trust_tier,state,source_kind,source_uri,"
            "session_id,turn_id,actor,evidence_hash,created_at,signature,key_fingerprint)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid,
                content,
                "T0",
                "t0_staged",
                "operator",
                None,
                None,
                None,
                "operator",
                eh,
                now,
                signature,
                key_fingerprint,
            ),
        )
        self._ledger_append("t0_stage", mid, {"fingerprint": key_fingerprint, "eh": eh})
        self._conn.commit()
        return mid

    def activate_t0(self, item_id: str, *, signature: str) -> None:
        """Promote a staged T0 to active (never decays). Caller must have
        verified the second signature + review gap (see memory/t0.py)."""
        now = _now()
        self._conn.execute(
            "UPDATE memory SET state='active', verified_at=?, verdict='operator-signed',"
            " trust_score=1.0, last_reaffirmed_at=?, review_at=NULL, signature=? WHERE id=?",
            (now, now, signature, item_id),
        )
        self._ledger_append("t0_activate", item_id, {})
        self._conn.commit()

    def staged_t0(self) -> list[MemoryItem]:
        return self.by_state("t0_staged")

    def update_trust_score(self, item_id: str, score: float) -> None:
        self._conn.execute("UPDATE memory SET trust_score=? WHERE id=?", (score, item_id))

    def mark_rejected(self, item_id: str, *, reason: str) -> None:
        self._set_state(item_id, "rejected", "reject", {"reason": reason})
        self._conn.commit()

    def revoke_by_source(self, source_uri: str) -> list[str]:
        """Revoke all items from a source and everything derived from them
        (cascade, PLAN §4.5). Returns the ids revoked."""
        revoked: list[str] = []
        # Direct hits.
        rows = self._conn.execute(
            "SELECT id FROM memory WHERE source_uri=? AND state IN ('active','pending')",
            (source_uri,),
        ).fetchall()
        frontier = [r["id"] for r in rows]
        while frontier:
            cur = frontier.pop()
            self._set_state(cur, "revoked", "revoke", {"source": source_uri})
            revoked.append(cur)
            children = self._conn.execute(
                "SELECT id FROM memory WHERE derived_from=? AND state IN ('active','pending')",
                (cur,),
            ).fetchall()
            frontier.extend(c["id"] for c in children)
        self._conn.commit()
        return revoked

    def expire_due(self, now: float | None = None) -> list[str]:
        now = now or _now()
        rows = self._conn.execute(
            "SELECT id FROM memory WHERE state='active' AND expires_at IS NOT NULL "
            "AND expires_at < ?",
            (now,),
        ).fetchall()
        ids = [r["id"] for r in rows]
        for mid in ids:
            self._set_state(mid, "expired", "expire", {})
        if ids:
            self._conn.commit()
        return ids

    def set_expiry(self, item_id: str, expires_at: float) -> None:
        self._conn.execute("UPDATE memory SET expires_at=? WHERE id=?", (expires_at, item_id))
        self._conn.commit()

    def add_confirmation(self, item_id: str) -> int:
        self._conn.execute(
            "UPDATE memory SET confirmations = confirmations + 1 WHERE id=?",
            (item_id,),
        )
        row = self._conn.execute(
            "SELECT confirmations FROM memory WHERE id=?", (item_id,)
        ).fetchone()
        self._conn.commit()
        return row["confirmations"] if row else 0

    # --- negative memory ------------------------------------------------

    def add_negative(self, content: str, *, reason: str, source_uri: str | None) -> str:
        nid = f"neg_{uuid.uuid4().hex[:10]}"
        self._conn.execute(
            "INSERT INTO negative_memory(id,content,reason,source_uri,created_at) "
            "VALUES(?,?,?,?,?)",
            (nid, content, reason, source_uri, _now()),
        )
        self._conn.commit()
        return nid

    def negatives(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM negative_memory ORDER BY created_at DESC"
        ).fetchall()

    # --- queries --------------------------------------------------------

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            trust_tier=row["trust_tier"],
            state=row["state"],
            provenance=Provenance(
                source_kind=row["source_kind"],
                source_uri=row["source_uri"],
                session_id=row["session_id"],
                turn_id=row["turn_id"],
                actor=row["actor"],
            ),
            evidence_hash=row["evidence_hash"],
            created_at=row["created_at"],
            verified_at=row["verified_at"],
            verdict=row["verdict"],
            confirmations=row["confirmations"],
            expires_at=row["expires_at"],
            superseded_by=row["superseded_by"],
            trust_score=row["trust_score"],
            last_reaffirmed_at=row["last_reaffirmed_at"],
            review_at=row["review_at"],
            reaffirm_count=row["reaffirm_count"],
            trust_ceiling=row["trust_ceiling"],
            sensitivity=row["sensitivity"],
        )

    def get(self, item_id: str) -> MemoryItem | None:
        row = self._conn.execute("SELECT * FROM memory WHERE id=?", (item_id,)).fetchone()
        return self._row_to_item(row) if row else None

    def by_state(self, state: MemoryState, *, limit: int = 200) -> list[MemoryItem]:
        rows = self._conn.execute(
            "SELECT * FROM memory WHERE state=? ORDER BY created_at DESC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def active(self, *, limit: int = 200) -> list[MemoryItem]:
        return self.by_state("active", limit=limit)

    def active_by_actor(self, actor: str, *, limit: int = 200) -> list[MemoryItem]:
        """Active memory attributed to one user (provenance.actor). This is the
        per-user scoping the cross-session user model is built on — it keeps one
        user's profile out of another's view in a multi-user gateway."""
        rows = self._conn.execute(
            "SELECT * FROM memory WHERE state='active' AND actor=? "
            "ORDER BY created_at DESC LIMIT ?",
            (actor, limit),
        ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def find_similar_active(self, content: str, source_kind: SourceKind) -> MemoryItem | None:
        """Exact-content dedup within active memory (embedding-based similarity
        arrives with the optional vec layer in a later step)."""
        row = self._conn.execute(
            "SELECT * FROM memory WHERE state='active' AND content=? LIMIT 1",
            (content,),
        ).fetchone()
        return self._row_to_item(row) if row else None
