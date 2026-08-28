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
            return "empty memory proposal ignored"
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
            return f"added to memory (verified): {content[:60]}"
        if state == "rejected":
            item = pipeline.store.get(mid)
            return f"rejected: {item.verdict or 'verification failed'}"
        return "quarantined — awaiting verification/approval"

    async def search(args: dict[str, Any]) -> str:
        query = args.get("query", "").strip()
        if not query:
            return "no matching memory"
        # Prefer trust-weighted semantic recall; fall back to substring when the
        # embedding layer is off or has nothing indexed yet.
        sem = getattr(pipeline, "semantic", None)
        if sem is not None and getattr(sem, "enabled", False):
            import asyncio

            recalls = await asyncio.to_thread(sem.recall, query)
            if recalls:
                return "\n".join(
                    f"[{r.item.trust_tier}] {r.item.content}  (~{r.score:.2f})" for r in recalls
                )
        q = query.casefold()
        hits = [m for m in pipeline.store.active() if q in m.content.casefold()]
        if not hits:
            return "no matching memory"
        return "\n".join(f"[{m.trust_tier}] {m.content}" for m in hits[:20])

    async def user_recall(args: dict[str, Any]) -> str:
        # Dialectic query over the CURRENT user's cross-session model only —
        # trust-weighted and scoped by user, so it never surfaces another user.
        question = args.get("query", "").strip()
        if not question or user_ref is None:
            return "no user model available"
        from milyonus.memory.usermodel import UserModel

        sem = getattr(pipeline, "semantic", None)
        model = UserModel(
            pipeline.store,
            user_ref=user_ref,
            config=pipeline.config,
            semantic=sem,
            pipeline=pipeline,
        )
        hits = model.ask(question)
        if not hits:
            return "nothing known about the user for that"
        return "\n".join(f"[{m.trust_tier} ~{score:.2f}] {m.content}" for m, score in hits)

    return [
        Tool(
            name="memory_propose",
            description=(
                "Propose a candidate for durable memory. Does not write directly — the "
                "candidate is quarantined and added only if it passes verification."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The fact to remember"},
                    "source_kind": {
                        "type": "string",
                        "enum": ["user-direct", "agent-observed"],
                        "description": "Use 'user-direct' if the user said it directly",
                    },
                },
                "required": ["content"],
            },
            handler=propose,
            risk="safe",
        ),
        Tool(
            name="memory_search",
            description="Search verified durable memory.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=search,
            risk="safe",
        ),
        Tool(
            name="user_recall",
            description=(
                "Ask what is known about the CURRENT user from their cross-session "
                "model (preferences, facts, patterns). Trust-weighted and scoped to "
                "this user only. Use it to personalize before assuming."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to recall about the user"}
                },
                "required": ["query"],
            },
            handler=user_recall,
            risk="safe",
        ),
    ]
