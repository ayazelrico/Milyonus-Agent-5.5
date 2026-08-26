"""Self-mod harness: snapshot, gate, auto-rollback on failing mutation."""

import subprocess

import pytest

from milyonus.selfmod.harness import SelfModHarness


def _init_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "file.txt").write_text("original\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    return SelfModHarness(tmp_path)


def test_non_git_reports_clearly(tmp_path):
    h = SelfModHarness(tmp_path)
    assert not h.is_git_repo()
    snap = h.snapshot("x")
    assert not snap.ok and "git" in snap.message


def test_snapshot_and_rollback(tmp_path):
    h = _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("changed\n")
    snap = h.snapshot("before more changes")
    assert snap.ok
    (tmp_path / "file.txt").write_text("more changes\n")
    h.snapshot("second")
    # Roll back to first snapshot.
    h.rollback(snap.ref)
    assert (tmp_path / "file.txt").read_text() == "changed\n"


def test_log_lists_snapshots(tmp_path):
    h = _init_repo(tmp_path)
    h.snapshot("alpha")
    h.snapshot("beta")
    entries = h.log()
    assert any("alpha" in e for e in entries)
    assert any("beta" in e for e in entries)


@pytest.mark.asyncio
async def test_apply_change_rolls_back_on_bad_mutation(tmp_path):
    h = _init_repo(tmp_path)

    async def bad_mutate():
        raise RuntimeError("boom")

    kept, msg = await h.apply_change("risky", bad_mutate)
    assert not kept
    assert "geri alındı" in msg
    assert (tmp_path / "file.txt").read_text() == "original\n"
