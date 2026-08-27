"""Vision: image sent as an ImageBlock; path-confined; scripted provider."""

import base64
from collections.abc import AsyncIterator

import pytest

from milyonus.providers.base import CompletionRequest, StreamEvent, Usage
from milyonus.tools.vision.tools import make_vision_tools

pytestmark = pytest.mark.asyncio

# 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class VisionProvider:
    name = "fake"
    model = "fake"

    def __init__(self):
        self.saw_image = False

    async def stream(self, req: CompletionRequest) -> AsyncIterator[StreamEvent]:
        # Confirm the image reached the request as an ImageBlock.
        self.saw_image = bool(req.messages[0].images)
        yield StreamEvent(kind="text", delta="a tiny transparent pixel")
        yield StreamEvent(kind="usage", usage=Usage(input_tokens=5, output_tokens=5))
        yield StreamEvent(kind="done", stop_reason="end_turn")


async def test_describe_image(tmp_path):
    (tmp_path / "pic.png").write_bytes(_PNG)
    prov = VisionProvider()
    tool = make_vision_tools(prov, tmp_path)[0]
    out = await tool.handler({"path": "pic.png", "question": "What is this?"})
    assert "pixel" in out
    assert prov.saw_image is True
    assert tool.risk == "safe"


async def test_missing_image(tmp_path):
    tool = make_vision_tools(VisionProvider(), tmp_path)[0]
    out = await tool.handler({"path": "nope.png"})
    assert "not found" in out


async def test_unsupported_type(tmp_path):
    (tmp_path / "file.txt").write_text("x")
    tool = make_vision_tools(VisionProvider(), tmp_path)[0]
    out = await tool.handler({"path": "file.txt"})
    assert "unsupported" in out


async def test_path_escape_blocked(tmp_path):
    tool = make_vision_tools(VisionProvider(), tmp_path)[0]
    out = await tool.handler({"path": "../../etc/passwd"})
    assert "outside the working root" in out
