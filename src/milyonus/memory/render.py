"""Render durable memory into the frozen L1 snapshot for the system prompt.

The snapshot is built once at session start (PLAN §4.6) so the prompt prefix
stays cache-stable. Active memories are grouped into a user profile and agent
notes, each capped to its character budget; the highest-trust, most-recent items
win when trimming. Each line keeps a trust tag so the not-instructions rule in
the prompt applies with visible provenance.
"""

from __future__ import annotations

from milyonus.config.schema import MemoryConfig
from milyonus.memory.model import MemoryItem
from milyonus.memory.store import MemoryStore
from milyonus.prompt.builder import MemorySnapshot

_TIER_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


def _fmt(item: MemoryItem) -> str:
    return f"[{item.trust_tier}] {item.content.strip()}"


def _pack(items: list[MemoryItem], budget: int) -> str:
    # Highest trust first (T0<T1<...), then most recent.
    ordered = sorted(items, key=lambda m: (_TIER_RANK.get(m.trust_tier, 9), -m.created_at))
    lines: list[str] = []
    used = 0
    for it in ordered:
        line = _fmt(it)
        if used + len(line) + 1 > budget:
            continue
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def _is_user_profile(item: MemoryItem) -> bool:
    return item.provenance.source_kind in ("user-direct", "operator")


def build_snapshot(store: MemoryStore, *, config: MemoryConfig | None = None) -> MemorySnapshot:
    config = config or MemoryConfig()
    active = store.active()
    user_items = [m for m in active if _is_user_profile(m)]
    agent_items = [m for m in active if not _is_user_profile(m)]
    return MemorySnapshot(
        user_profile=_pack(user_items, config.user_profile_chars),
        agent_notes=_pack(agent_items, config.agent_profile_chars),
    )
