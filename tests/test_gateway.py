"""Gateway: default-deny, in-chat pairing, and an authorized turn — all with a
fake adapter and scripted provider (no network, no API key)."""

from collections.abc import AsyncIterator

import pytest

from milyonus.config.schema import MilyonusConfig, ProviderConfig
from milyonus.gateway.adapter import InboundMessage, OutboundMessage
from milyonus.gateway.pairing import PairingManager
from milyonus.gateway.server import GatewayServer
from milyonus.memory.store import MemoryStore
from milyonus.providers.base import CompletionRequest, StreamEvent, Usage

pytestmark = pytest.mark.asyncio


class FakeAdapter:
    name = "telegram"

    def __init__(self):
        self.sent: list[OutboundMessage] = []
        self.approval_answer = True

    async def start(self, handler):  # pragma: no cover - not used directly
        return None

    async def send(self, message: OutboundMessage) -> None:
        self.sent.append(message)

    async def ask_approval(self, user_id: str, prompt: str) -> bool:
        return self.approval_answer


class ScriptedProvider:
    name = "fake"
    model = "fake"

    def __init__(self, text: str):
        self._text = text

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(kind="text", delta=self._text)
        yield StreamEvent(kind="usage", usage=Usage(input_tokens=5, output_tokens=3))
        yield StreamEvent(kind="done", stop_reason="end_turn")


def _server(tmp_path, adapter):
    cfg = MilyonusConfig(provider=ProviderConfig(name="anthropic"))
    srv = GatewayServer(
        cfg,
        [adapter],
        workspace=tmp_path,
        pairing=PairingManager(tmp_path / "pairing.json"),
        mem_store=MemoryStore(tmp_path / "state.db"),
    )
    srv.provider = ScriptedProvider("Merhaba, ben Milyonus.")
    return srv


async def test_unpaired_user_denied(tmp_path):
    adapter = FakeAdapter()
    srv = _server(tmp_path, adapter)
    await srv.handle(adapter, InboundMessage("telegram", "u1", "selam"))
    assert any("pairing" in m.text.lower() for m in adapter.sent)


async def test_pairing_flow(tmp_path):
    adapter = FakeAdapter()
    srv = _server(tmp_path, adapter)
    code = srv.pairing.new_code("telegram")
    await srv.handle(adapter, InboundMessage("telegram", "u1", f"/pair {code}"))
    assert srv.pairing.is_paired("telegram", "u1")
    assert any("successful" in m.text for m in adapter.sent)


async def test_authorized_turn(tmp_path):
    adapter = FakeAdapter()
    srv = _server(tmp_path, adapter)
    code = srv.pairing.new_code("telegram")
    await srv.handle(adapter, InboundMessage("telegram", "u1", f"/pair {code}"))
    adapter.sent.clear()
    await srv.handle(adapter, InboundMessage("telegram", "u1", "kimsin?"))
    assert any("Milyonus" in m.text for m in adapter.sent)


async def test_allow_all_bypasses_pairing(tmp_path):
    adapter = FakeAdapter()
    cfg = MilyonusConfig(provider=ProviderConfig())
    cfg.security.gateway_allow_all_users = True
    srv = GatewayServer(
        cfg,
        [adapter],
        workspace=tmp_path,
        pairing=PairingManager(tmp_path / "p.json"),
        mem_store=MemoryStore(tmp_path / "s.db"),
    )
    srv.provider = ScriptedProvider("cevap")
    await srv.handle(adapter, InboundMessage("telegram", "u2", "selam"))
    assert any("cevap" in m.text for m in adapter.sent)


async def test_run_reconnects_on_failure(tmp_path, monkeypatch):
    """A failing adapter is retried with backoff, not fatal to the gateway."""
    adapter = FakeAdapter()
    srv = _server(tmp_path, adapter)

    calls = {"n": 0}

    async def flaky_start(handler):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("drop")
        return  # third attempt succeeds and returns cleanly

    adapter.start = flaky_start
    # Speed up backoff sleeps.
    import milyonus.gateway.server as srvmod

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(srvmod.asyncio, "sleep", fast_sleep)
    await srv.run()
    assert calls["n"] == 3  # retried twice, succeeded on the third
