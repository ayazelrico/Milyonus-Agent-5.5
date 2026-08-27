"""Vector index — persistent cosine store keyed by memory id.

Vectors live in a `memory_vector` table in the same SQLite file as the rest of
durable memory, so a backup or `state.db` copy carries the embeddings with it.
Vectors are stored as packed float32 blobs (no numpy dependency) and are already
L2-normalized by the embedder, so cosine similarity is a dot product.

The index is a pure convenience layer over the authoritative `memory` table: it
never holds a fact that isn't in the store, and `search` can be constrained to a
set of allowed ids (callers pass the *active* set) so demoted or rejected memory
cannot be recalled. If `sqlite-vec` is installed it can accelerate large stores,
but the default path is plain Python and works everywhere.
"""

from __future__ import annotations

import sqlite3
from array import array
from pathlib import Path

from milyonus.config.paths import state_db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_vector (
    id        TEXT PRIMARY KEY,
    model     TEXT NOT NULL,
    dim       INTEGER NOT NULL,
    vec       BLOB NOT NULL,
    updated_at REAL NOT NULL
);
"""


def _pack(vec: list[float]) -> bytes:
    return array("f", vec).tobytes()


def _unpack(blob: bytes) -> list[float]:
    a = array("f")
    a.frombytes(blob)
    return a.tolist()


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


class VectorIndex:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_db()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, item_id: str, vec: list[float], *, model: str) -> None:
        import time

        self._conn.execute(
            "INSERT INTO memory_vector(id,model,dim,vec,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET model=excluded.model, dim=excluded.dim, "
            "vec=excluded.vec, updated_at=excluded.updated_at",
            (item_id, model, len(vec), _pack(vec), time.time()),
        )
        self._conn.commit()

    def delete(self, item_id: str) -> None:
        self._conn.execute("DELETE FROM memory_vector WHERE id=?", (item_id,))
        self._conn.commit()

    def has(self, item_id: str, *, model: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM memory_vector WHERE id=? AND model=?", (item_id, model)
        ).fetchone()
        return row is not None

    def count(self, *, model: str | None = None) -> int:
        if model is None:
            row = self._conn.execute("SELECT COUNT(*) c FROM memory_vector").fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) c FROM memory_vector WHERE model=?", (model,)
            ).fetchone()
        return int(row["c"])

    def search(
        self,
        query_vec: list[float],
        *,
        model: str,
        k: int = 8,
        allowed_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return the top-k (id, cosine) for vectors from the same embedder,
        optionally restricted to `allowed_ids` (e.g. only active memory)."""
        rows = self._conn.execute(
            "SELECT id, vec FROM memory_vector WHERE model=?", (model,)
        ).fetchall()
        scored: list[tuple[str, float]] = []
        for r in rows:
            if allowed_ids is not None and r["id"] not in allowed_ids:
                continue
            scored.append((r["id"], _dot(query_vec, _unpack(r["vec"]))))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]
