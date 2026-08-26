"""L1 snapshot: active memory renders into fenced user/agent sections with tags."""

from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.render import build_snapshot
from milyonus.memory.store import MemoryStore
from milyonus.prompt.builder import build_system_prompt


async def _seed(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    p = MemoryPipeline(store)
    u = p.propose("Kullanıcı Türkçe konuşur", source_kind="user-direct")
    await p.process_one(u)
    a = p.propose("Proje adı Milyonus", source_kind="agent-observed")
    await p.process_one(a)
    return store


async def test_snapshot_groups(tmp_path):
    store = await _seed(tmp_path)
    snap = build_snapshot(store)
    assert "Türkçe" in snap.user_profile
    assert "Milyonus" in snap.agent_notes
    assert "[T1]" in snap.user_profile


async def test_snapshot_into_prompt_is_fenced(tmp_path):
    store = await _seed(tmp_path)
    snap = build_snapshot(store)
    prompt = build_system_prompt(memory=snap)
    assert "<milyonus:memory" in prompt
    assert "PAST OBSERVATIONS" in prompt


async def test_budget_trims(tmp_path):
    store = MemoryStore(tmp_path / "state.db")
    p = MemoryPipeline(store)
    for i in range(50):
        mid = p.propose(f"olgu numarası {i} " + "x" * 50, source_kind="user-direct")
        await p.process_one(mid)
    from milyonus.config.schema import MemoryConfig

    snap = build_snapshot(store, config=MemoryConfig(user_profile_chars=500))
    assert len(snap.user_profile) <= 500
