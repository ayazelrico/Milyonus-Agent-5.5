"""Subagent delegation with a context contract (PLAN §8).

Hermes subagents start blank and rely on the parent to remember to pass context.
Milyonus requires a context contract: goal + non-empty context + success_criteria.
The framework assembles a briefing so the child is not flying blind, and the
child runs with a restricted toolset (no delegation/memory-write/send/clarify).
Child-produced memory is T4 (never auto-promotes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.providers.base import Message, Provider
from milyonus.tools.registry import ToolRegistry

# Toolsets always denied to children (PLAN §8).
_DENIED_TOOLS = {
    "delegate_task",
    "memory_propose",
    "skill_manage",
    "run_shell",
}


class ContractError(Exception):
    """Raised when a delegation is missing required contract fields."""


@dataclass(slots=True)
class DelegationContract:
    goal: str
    context: str
    success_criteria: list[str]
    inherited_facts: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.goal.strip():
            raise ContractError("goal cannot be empty")
        if not self.context.strip():
            raise ContractError(
                "context cannot be empty — the child agent does not know the parent"
            )
        if not self.success_criteria:
            raise ContractError("success_criteria cannot be empty")

    def briefing(self) -> str:
        parts = [f"# Task\n{self.goal}", f"# Context\n{self.context}"]
        if self.inherited_facts:
            facts = "\n".join(f"- {f}" for f in self.inherited_facts)
            parts.append(f"# Inherited facts\n{facts}")
        crit = "\n".join(f"- {c}" for c in self.success_criteria)
        parts.append(f"# Success criteria\n{crit}")
        if self.forbidden:
            forb = "\n".join(f"- {f}" for f in self.forbidden)
            parts.append(f"# Yapma\n{forb}")
        return "\n\n".join(parts)


def _restricted_registry(parent: ToolRegistry) -> ToolRegistry:
    child = ToolRegistry()
    for name in parent.names():
        if name in _DENIED_TOOLS:
            continue
        tool = parent.get(name)
        if tool is not None:
            child.register(tool)
    return child


async def run_subagent(
    contract: DelegationContract,
    *,
    provider: Provider,
    parent_tools: ToolRegistry,
    max_iterations: int = 50,
    max_output_tokens: int = 4096,
) -> str:
    """Run a child agent under the contract. Returns its final answer."""
    contract.validate()
    child_tools = _restricted_registry(parent_tools)
    system = (
        "You are a subagent. You know no history beyond the briefing you were "
        "given. Complete the task and return the result."
    )
    loop = AgentLoop(
        provider=provider,
        tools=child_tools,
        system_prompt=system,
        budget=Budget(max_iterations=max_iterations),
        max_output_tokens=max_output_tokens,
    )
    history = [Message(role="user", content=contract.briefing())]
    return await loop.run_turn(history)
