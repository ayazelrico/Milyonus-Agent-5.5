"""Provider-agnostic message types and the Provider protocol.

The core agent loop speaks only these types. Each concrete provider
(Anthropic, OpenAI-compatible) translates them to and from its wire format.
Keeping this layer thin and neutral is what makes the core provider-agnostic
(ADR-002) and lets a verifier model run on a different backend than the main one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class ToolCall:
    """A model's request to invoke a tool."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    """The outcome of a tool invocation, fed back to the model."""

    call_id: str
    content: str
    is_error: bool = False


@dataclass(slots=True)
class Message:
    """One turn in the conversation, in neutral form."""

    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


@dataclass(slots=True)
class ToolSchema:
    """A tool definition offered to the model."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments object


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(slots=True)
class StreamEvent:
    """One incremental event from a streaming completion.

    kind:
      "text"       -> delta carries a chunk of assistant text
      "tool_call"  -> tool_call is a fully-assembled ToolCall
      "usage"      -> usage carries token counts (usually at the end)
      "done"       -> stop_reason carries why generation ended
    """

    kind: Literal["text", "tool_call", "usage", "done"]
    delta: str = ""
    tool_call: ToolCall | None = None
    usage: Usage | None = None
    stop_reason: str | None = None


@dataclass(slots=True)
class CompletionRequest:
    system: str
    messages: Sequence[Message]
    tools: Sequence[ToolSchema] = ()
    max_output_tokens: int = 4096
    temperature: float = 1.0


class ProviderError(Exception):
    """Raised when a provider call fails in a way the loop should surface."""


@runtime_checkable
class Provider(Protocol):
    """The interface every backend implements."""

    name: str
    model: str

    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvents for a completion. Must be cancellable (the loop
        may stop iterating early to interrupt generation)."""
        ...
