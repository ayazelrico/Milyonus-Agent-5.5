"""The `memory` tool the agent calls — proposals only, never direct writes.

The agent has exactly one way to affect durable memory: propose a candidate,
which is quarantined and later verified (PLAN §4.3). There is deliberately no
"memory.write" that lands in active state. `memory.search` reads active memory.
The user-facing action, tier resolution, and verification all happen behind this
tool, so a compromised agent cannot bypass the pipeline.
"""

from __future__ import annotations

from typing import Any

from milyonus.memory.pipeline import MemoryPipeline
from milyonus.tools.registry import Tool


def make_memory_tools(
    pipeline: MemoryPipeline,
    *,
    session_id: str | None,
    user_ref: str | None,
    default_source: str = "agent-observed",
) -> list[Tool]:
    async def propose(args: dict[str, Any]) -> str:
        content = args["content"].strip()
        if not content:
            return "boş bellek önerisi yok sayıldı"
        # An agent proposing about the user's own stated preference is treated as
        # user-direct only when the caller marks it so; default is agent-observed.
        source = args.get("source_kind", default_source)
        if source not in ("user-direct", "agent-observed"):
            source = default_source  # the agent cannot self-declare third-party trust
        mid = pipeline.propose(
            content,
            source_kind=source,  # type: ignore[arg-type]
            session_id=session_id,
            actor=user_ref,
        )
        state = await pipeline.process_one(mid)
        if state == "active":
            return f"belleğe eklendi (doğrulandı): {content[:60]}"
        if state == "rejected":
            item = pipeline.store.get(mid)
            return f"reddedildi: {item.verdict or 'doğrulama başarısız'}"
        return "karantinada — doğrulama/onay bekliyor"

    async def search(args: dict[str, Any]) -> str:
        query = args.get("query", "").casefold()
        hits = [m for m in pipeline.store.active() if query in m.content.casefold()]
        if not hits:
            return "eşleşen bellek yok"
        return "\n".join(f"[{m.trust_tier}] {m.content}" for m in hits[:20])

    return [
        Tool(
            name="memory_propose",
            description=(
                "Kalıcı bellek için bir aday önerir. Doğrudan yazmaz — aday "
                "karantinaya alınır ve doğrulamadan geçerse eklenir."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Hatırlanacak olgu"},
                    "source_kind": {
                        "type": "string",
                        "enum": ["user-direct", "agent-observed"],
                        "description": "Kullanıcı doğrudan söylediyse 'user-direct'",
                    },
                },
                "required": ["content"],
            },
            handler=propose,
            risk="safe",
        ),
        Tool(
            name="memory_search",
            description="Doğrulanmış kalıcı bellekte arama yapar.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=search,
            risk="safe",
        ),
    ]
