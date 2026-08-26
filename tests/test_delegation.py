"""Subagent delegation: the context contract is enforced and toolsets restricted."""

from collections.abc import AsyncIterator

import pytest

from milyonus.delegation.subagent import (
    ContractError,
    DelegationContract,
    _restricted_registry,
    run_subagent,
)
from milyonus.providers.base import CompletionRequest, StreamEvent, Usage
from milyonus.tools.registry import Tool, ToolRegistry


def test_contract_requires_context():
    c = DelegationContract(goal="yap", context="", success_criteria=["bitir"])
    with pytest.raises(ContractError):
        c.validate()


def test_contract_requires_success_criteria():
    c = DelegationContract(goal="yap", context="bağlam", success_criteria=[])
    with pytest.raises(ContractError):
        c.validate()


def test_briefing_includes_all_sections():
    c = DelegationContract(
        goal="G",
        context="C",
        success_criteria=["S1"],
        inherited_facts=["F1"],
        forbidden=["X"],
    )
    b = c.briefing()
    assert "G" in b and "C" in b and "S1" in b and "F1" in b and "X" in b


def test_restricted_registry_drops_dangerous():
    reg = ToolRegistry()
    for name in ("read_file", "run_shell", "memory_propose", "delegate_task"):
        reg.register(
            Tool(name=name, description="d", parameters={"type": "object"}, handler=None)  # type: ignore[arg-type]
        )
    child = _restricted_registry(reg)
    assert "read_file" in child.names()
    assert "run_shell" not in child.names()
    assert "memory_propose" not in child.names()
    assert "delegate_task" not in child.names()


class ScriptedProvider:
    name = "fake"
    model = "fake"

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        # Confirm the briefing reached the child.
        assert "Success criteria" in request.messages[0].content
        yield StreamEvent(kind="text", delta="alt görev tamam")
        yield StreamEvent(kind="usage", usage=Usage(input_tokens=1, output_tokens=1))
        yield StreamEvent(kind="done", stop_reason="end_turn")


@pytest.mark.asyncio
async def test_run_subagent():
    contract = DelegationContract(
        goal="dosyayı say", context="proje kökünde çalış", success_criteria=["sayı döndür"]
    )
    result = await run_subagent(contract, provider=ScriptedProvider(), parent_tools=ToolRegistry())
    assert result == "alt görev tamam"
