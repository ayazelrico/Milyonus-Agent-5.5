"""MCP server configuration + manager: connect, namespace, isolate failures."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from milyonus.config.schema import MCPServerConfig, MilyonusConfig
from milyonus.tools.mcp.manager import MCPManager
from milyonus.tools.registry import ToolRegistry

_FAKE = Path(__file__).parent / "_fake_mcp_server.py"


def _server(name: str, *, enabled: bool = True, risk: str = "caution") -> MCPServerConfig:
    return MCPServerConfig(
        name=name,
        command=[sys.executable, str(_FAKE)],
        enabled=enabled,
        risk=risk,
    )


# --- config validation ------------------------------------------------------


def test_config_rejects_bad_name():
    with pytest.raises(ValidationError):
        MCPServerConfig(name="Bad Name!", command=["x"])


def test_config_rejects_empty_command():
    with pytest.raises(ValidationError):
        MCPServerConfig(name="ok", command=[])


def test_top_level_config_defaults_empty():
    assert MilyonusConfig().mcp_servers == []


# --- manager: connect + namespace + call ------------------------------------


async def test_manager_connects_and_namespaces():
    mgr = MCPManager([_server("demo")])
    await mgr.start()
    try:
        assert not mgr.errors
        tools = mgr.tools()
        assert [t.name for t in tools] == ["mcp_demo_echo"]
        assert tools[0].risk == "caution"
        out, is_err = await tools[0].handler({"text": "hi"}), False
        assert out == "echo: hi" and not is_err
    finally:
        await mgr.close()


async def test_risk_override_applied():
    mgr = MCPManager([_server("danger", risk="danger")])
    await mgr.start()
    try:
        assert mgr.tools()[0].risk == "danger"
    finally:
        await mgr.close()


async def test_disabled_server_skipped():
    mgr = MCPManager([_server("off", enabled=False)])
    await mgr.start()
    assert mgr.tools() == [] and not mgr.errors
    await mgr.close()


async def test_failing_server_isolated():
    good = _server("good")
    bad = MCPServerConfig(name="bad", command=["definitely-not-a-real-binary-xyz"])
    mgr = MCPManager([bad, good])
    await mgr.start()
    try:
        # the bad server is recorded but the good one still connects
        assert "bad" in mgr.errors
        assert [t.name for t in mgr.tools()] == ["mcp_good_echo"]
    finally:
        await mgr.close()


async def test_register_into_skips_collisions():
    reg = ToolRegistry()
    mgr = MCPManager([_server("demo")])
    await mgr.start()
    try:
        assert mgr.register_into(reg) == 1
        assert "mcp_demo_echo" in reg.names()
        # second registration of the same tool name is skipped, not an error
        assert mgr.register_into(reg) == 0
    finally:
        await mgr.close()
