"""Tool registry and the Tool interface.

A Tool exposes a JSON-Schema signature to the model and an async `run`. The
registry turns registered tools into the ToolSchema list the provider sends, and
dispatches a ToolCall to the right handler. Risk classification lives on the tool
so the RiskEngine (F4) can gate execution; in F1 the loop honors a simple
`requires_approval` flag.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from milyonus.providers.base import ToolSchema

RiskLevel = Literal["safe", "caution", "danger"]

Handler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(slots=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler
    # Reversibility drives approval (ADR-004/PLAN §6.1). "danger" means the
    # effect is hard to undo or reaches outside the machine -> always confirm.
    risk: RiskLevel = "safe"

    def schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.parameters)


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[ToolSchema]:
        return [t.schema() for t in self._tools.values()]

    async def run(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Execute a tool. Returns (content, is_error)."""
        tool = self._tools.get(name)
        if tool is None:
            return (f"Unknown tool: {name}", True)
        try:
            return (await tool.handler(args), False)
        except Exception as exc:  # tools surface errors as tool results, not crashes
            return (f"{type(exc).__name__}: {exc}", True)
