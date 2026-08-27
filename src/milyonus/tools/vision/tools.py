"""Vision tool — analyze a local image with a multimodal model.

`describe_image` reads a local image (path-confined to the working root),
base64-encodes it, and runs a one-shot completion with the image + a question.
Works with any provider whose model accepts image input (Anthropic, OpenAI). The
image is passed as a neutral ImageBlock, so no provider-specific code lives here.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from milyonus.providers.base import (
    CompletionRequest,
    ImageBlock,
    Message,
    Provider,
    ProviderError,
)
from milyonus.tools.registry import Tool

_MEDIA = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_MAX_BYTES = 5_000_000  # 5 MB


def _resolve(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    root_r = root.resolve()
    if p != root_r and root_r not in p.parents:
        raise ValueError(f"path outside the working root: {rel}")
    return p


def make_vision_tools(
    provider: Provider, root: Path, *, max_output_tokens: int = 1024
) -> list[Tool]:
    root = root.resolve()

    async def describe_image(args: dict[str, Any]) -> str:
        rel = args["path"]
        question = args.get("question", "Describe this image in detail.")
        try:
            path = _resolve(root, rel)
        except ValueError as exc:
            return str(exc)
        if not path.exists():
            return f"image not found: {rel}"
        media = _MEDIA.get(path.suffix.lower())
        if media is None:
            return f"unsupported image type: {path.suffix} (png/jpg/gif/webp)"
        data = path.read_bytes()
        if len(data) > _MAX_BYTES:
            return f"image too large ({len(data)} bytes, max {_MAX_BYTES})"
        b64 = base64.b64encode(data).decode("ascii")
        req = CompletionRequest(
            system="You are a precise visual analyst. Answer only about the image.",
            messages=[
                Message(
                    role="user",
                    content=question,
                    images=[ImageBlock(media_type=media, data=b64)],
                )
            ],
            max_output_tokens=max_output_tokens,
        )
        try:
            text = ""
            async for ev in provider.stream(req):
                if ev.kind == "text":
                    text += ev.delta
            return text or "(no description)"
        except ProviderError as exc:
            return f"vision error: {exc}"

    return [
        Tool(
            name="describe_image",
            description=(
                "Analyze a local image (png/jpg/gif/webp) and answer a question "
                "about it. Path is relative to the working root."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative image path"},
                    "question": {"type": "string"},
                },
                "required": ["path"],
            },
            handler=describe_image,
            risk="safe",  # read-only, local
        ),
    ]
