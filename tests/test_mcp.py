"""MCP client: initialize, list tools, call a tool — against a fake stdio server."""

import sys
from pathlib import Path

import pytest

from milyonus.tools.mcp.client import MCPClient

pytestmark = pytest.mark.asyncio

_SERVER = str(Path(__file__).parent / "_fake_mcp_server.py")


async def test_list_and_call():
    client = MCPClient([sys.executable, _SERVER])
    await client.start()
    try:
        tools = await client.list_tools()
        assert any(t["name"] == "echo" for t in tools)
        result = await client.call_tool("echo", {"text": "merhaba"})
        assert result == "echo: merhaba"
    finally:
        await client.close()


async def test_as_tools_namespaced():
    client = MCPClient([sys.executable, _SERVER])
    await client.start()
    try:
        tools = await client.as_tools(prefix="fake")
        assert tools[0].name == "fake_echo"
        assert tools[0].risk == "caution"  # external = caution
        out = await tools[0].handler({"text": "x"})
        assert out == "echo: x"
    finally:
        await client.close()
