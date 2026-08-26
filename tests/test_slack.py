"""Slack adapter: url_verification, signature (replay-protected), event parsing."""

import hashlib
import hmac
import json
import time

import pytest

from milyonus.gateway.adapters.slack import SlackAdapter
from milyonus.gateway.webhook import Request

pytestmark = pytest.mark.asyncio


def _adapter(**kw):
    return SlackAdapter(bot_token="xoxb-t", **kw)


def _req(body: bytes, headers=None):
    return Request("POST", "/slack", "", headers or {}, body)


async def test_url_verification():
    a = _adapter()
    body = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode()
    status, out = await a._on_request(_req(body))
    assert status == 200 and out == "abc123"


async def test_message_event_parsed():
    a = _adapter()
    msg = a.parse_event(
        {"event": {"type": "message", "text": "selam", "channel": "C1", "user": "U1"}}
    )
    assert msg is not None and msg.text == "selam" and msg.user_id == "C1"


async def test_bot_message_ignored():
    a = _adapter()
    msg = a.parse_event(
        {"event": {"type": "message", "text": "x", "channel": "C1", "bot_id": "B1"}}
    )
    assert msg is None


async def test_signature_valid():
    a = _adapter(signing_secret="shh")
    body = json.dumps({"type": "event_callback"}).encode()
    ts = str(int(time.time()))
    base = f"v0:{ts}:{body.decode()}".encode()
    sig = "v0=" + hmac.new(b"shh", base, hashlib.sha256).hexdigest()
    assert a.verify_signature({"x-slack-request-timestamp": ts, "x-slack-signature": sig}, body)


async def test_signature_replay_rejected():
    a = _adapter(signing_secret="shh")
    body = b"{}"
    old_ts = str(int(time.time()) - 1000)  # older than 5 min
    base = f"v0:{old_ts}:{body.decode()}".encode()
    sig = "v0=" + hmac.new(b"shh", base, hashlib.sha256).hexdigest()
    assert not a.verify_signature(
        {"x-slack-request-timestamp": old_ts, "x-slack-signature": sig}, body
    )


async def test_bad_signature_over_request():
    a = _adapter(signing_secret="shh")
    body = json.dumps({"type": "event_callback"}).encode()
    status, _ = await a._on_request(
        _req(
            body,
            {"x-slack-request-timestamp": str(int(time.time())), "x-slack-signature": "v0=wrong"},
        )
    )
    assert status == 401


async def test_event_dedup():
    a = _adapter()
    payload = {
        "type": "event_callback",
        "event_id": "Ev1",
        "event": {"type": "message", "text": "hi", "channel": "C1"},
    }
    body = json.dumps(payload).encode()
    await a._on_request(_req(body))
    assert a._queue.qsize() == 1
    await a._on_request(_req(body))  # retry with same event_id
    assert a._queue.qsize() == 1  # not enqueued twice
