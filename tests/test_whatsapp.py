"""WhatsApp Cloud adapter: webhook verify, HMAC signature, inbound parsing,
and a real end-to-end HTTP round-trip over a local socket."""

import asyncio
import hashlib
import hmac
import json

import httpx
import pytest

from milyonus.gateway.adapters.whatsapp import WhatsAppCloudAdapter

pytestmark = pytest.mark.asyncio

WEBHOOK_PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "contacts": [{"wa_id": "905551112233", "profile": {"name": "Ayaz"}}],
                        "messages": [
                            {"from": "905551112233", "type": "text", "text": {"body": "merhaba"}}
                        ],
                    }
                }
            ]
        }
    ]
}


def _adapter(**kw):
    return WhatsAppCloudAdapter(token="t", phone_number_id="pid", verify_token="VT", **kw)


async def test_webhook_verification_ok():
    a = _adapter()
    status, body = a.handle_verification("hub.mode=subscribe&hub.verify_token=VT&hub.challenge=42")
    assert status == 200 and body == "42"


async def test_webhook_verification_wrong_token():
    a = _adapter()
    status, _ = a.handle_verification("hub.mode=subscribe&hub.verify_token=WRONG&hub.challenge=42")
    assert status == 403


async def test_parse_inbound():
    a = _adapter()
    msgs = a.parse_inbound(WEBHOOK_PAYLOAD)
    assert len(msgs) == 1
    assert msgs[0].user_id == "905551112233"
    assert msgs[0].text == "merhaba"
    assert msgs[0].display_name == "Ayaz"
    assert msgs[0].channel == "whatsapp"


async def test_signature_required_when_secret_set():
    a = _adapter(app_secret="s3cr3t")
    raw = json.dumps(WEBHOOK_PAYLOAD).encode()
    good = "sha256=" + hmac.new(b"s3cr3t", raw, hashlib.sha256).hexdigest()
    assert a.verify_signature(raw, good) is True
    assert a.verify_signature(raw, "sha256=deadbeef") is False
    assert a.verify_signature(raw, None) is False


async def test_no_signature_check_without_secret():
    a = _adapter()  # no app secret
    assert a.verify_signature(b"anything", None) is True


async def test_end_to_end_http_roundtrip():
    a = _adapter(app_secret="s3cr3t", port=0)
    received: list = []

    async def handler(msg):
        received.append(msg)

    asyncio.create_task(a._dispatch_inbound(handler))
    server = await asyncio.start_server(a._handle_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        raw = json.dumps(WEBHOOK_PAYLOAD).encode()
        sig = "sha256=" + hmac.new(b"s3cr3t", raw, hashlib.sha256).hexdigest()
        async with httpx.AsyncClient() as client:
            # GET verify
            r = await client.get(
                f"http://127.0.0.1:{port}/webhook",
                params={"hub.mode": "subscribe", "hub.verify_token": "VT", "hub.challenge": "99"},
            )
            assert r.status_code == 200 and r.text == "99"
            # POST inbound with valid signature
            r2 = await client.post(
                f"http://127.0.0.1:{port}/webhook",
                content=raw,
                headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
            )
            assert r2.status_code == 200
        # give the dispatcher a tick to process the queue
        await asyncio.sleep(0.05)
    assert len(received) == 1 and received[0].text == "merhaba"


async def test_bad_signature_rejected_over_http():
    a = _adapter(app_secret="s3cr3t")
    server = await asyncio.start_server(a._handle_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server, httpx.AsyncClient() as client:
        r = await client.post(
            f"http://127.0.0.1:{port}/webhook",
            content=json.dumps(WEBHOOK_PAYLOAD).encode(),
            headers={"X-Hub-Signature-256": "sha256=wrong"},
        )
        assert r.status_code == 401
