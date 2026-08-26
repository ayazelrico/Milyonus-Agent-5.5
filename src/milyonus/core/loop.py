"""The agent loop — the single core every surface (CLI, gateway, cron) shares.

One turn: build the request from history, stream a completion, and if the model
asked for tools, execute them (via an approval hook) and feed results back until
the model produces a final answer or the budget is exhausted. Streaming text is
delivered through an async callback so the TUI can render tokens live.

Security posture in F1: dangerous tools are gated by `approve`, an injected
callback. F4 replaces the default approve with the RiskEngine.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from milyonus.core.budget import Budget
from milyonus.providers.base import (
    CompletionRequest,
    Message,
    Provider,
    ToolCall,
    ToolResult,
)
from milyonus.tools.registry import ToolRegistry

# Called before a non-safe tool runs. Returns True to allow. Default: allow all
# (F1); the CLI supplies an interactive prompt, F4 supplies the RiskEngine.
ApproveFn = Callable[[ToolCall, str], Awaitable[bool]]

# Streaming sinks. on_text gets assistant text chunks; on_tool announces a call.
TextSink = Callable[[str], Awaitable[None]]
ToolSink = Callable[[ToolCall], Awaitable[None]]


async def _allow_all(_call: ToolCall, _risk: str) -> bool:
    return True


async def _noop_text(_s: str) -> None:  # pragma: no cover - trivial
    return None


async def _noop_tool(_c: ToolCall) -> None:  # pragma: no cover - trivial
    return None


@dataclass
class AgentLoop:
    provider: Provider
    tools: ToolRegistry
    system_prompt: str
    budget: Budget = field(default_factory=Budget)
    approve: ApproveFn = _allow_all
    on_text: TextSink = _noop_text
    on_tool: ToolSink = _noop_tool
    max_output_tokens: int = 4096

    async def run_turn(self, history: list[Message]) -> str:
        """Advance the conversation until a final assistant message. `history`
        is mutated in place with the new assistant/tool messages."""
        while True:
            if self.budget.exhausted():
                note = "(bütçe tükendi — görev burada durduruldu)"
                history.append(Message(role="assistant", content=note))
                return note

            request = CompletionRequest(
                system=self.system_prompt,
                messages=history,
                tools=self.tools.schemas(),
                max_output_tokens=self.max_output_tokens,
            )

            text_parts: list[str] = []
            pending: list[ToolCall] = []
            async for event in self.provider.stream(request):
                if event.kind == "text":
                    text_parts.append(event.delta)
                    await self.on_text(event.delta)
                elif event.kind == "tool_call" and event.tool_call is not None:
                    pending.append(event.tool_call)
                    await self.on_tool(event.tool_call)
                elif event.kind == "usage" and event.usage is not None:
                    self.budget.record(
                        input_tokens=event.usage.input_tokens,
                        output_tokens=event.usage.output_tokens,
                    )

            assistant_text = "".join(text_parts)
            history.append(
                Message(
                    role="assistant",
                    content=assistant_text,
                    tool_calls=list(pending),
                )
            )

            if not pending:
                return assistant_text

            # Execute the requested tools and append their results.
            results: list[ToolResult] = []
            for call in pending:
                tool = self.tools.get(call.name)
                risk = tool.risk if tool else "danger"
                if risk != "safe":
                    ok = await self.approve(call, risk)
                    if not ok:
                        results.append(
                            ToolResult(
                                call_id=call.id,
                                content="(kullanıcı bu aracı reddetti)",
                                is_error=True,
                            )
                        )
                        continue
                content, is_error = await self.tools.run(call.name, call.arguments)
                results.append(ToolResult(call_id=call.id, content=content, is_error=is_error))
            history.append(Message(role="tool", tool_results=results))
            # loop continues: model sees tool results and responds


def build_history(user_messages: Sequence[str]) -> list[Message]:  # pragma: no cover
    return [Message(role="user", content=m) for m in user_messages]
