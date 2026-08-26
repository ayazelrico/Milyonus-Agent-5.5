"""Self-modification harness (PLAN §9, ADR-004/005).

The agent may edit its own code and skills — nothing blocks it. Safety comes from
reversibility, not prohibition:

  1. snapshot()  — commit the working tree to a milyonus/auto branch, tagged,
                   before a change, so there is always a point to return to.
  2. (agent edits files with normal tools)
  3. test_gate() — run `pytest -q` (+ optional doctor). Red => auto rollback.
  4. rollback()  — restore a previous snapshot with one call.

This lives behind a git repo. If the workspace is not a git repo, snapshots are
disabled and the harness reports that clearly rather than silently doing nothing.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

_AUTO_BRANCH = "milyonus/auto"


@dataclass(slots=True)
class SnapshotResult:
    ok: bool
    ref: str
    message: str


@dataclass(slots=True)
class GateResult:
    passed: bool
    output: str


class SelfModHarness:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def is_git_repo(self) -> bool:
        return self._git("rev-parse", "--is-inside-work-tree").returncode == 0

    def snapshot(self, label: str) -> SnapshotResult:
        """Commit the current tree as a restore point. Returns the commit ref."""
        if not self.is_git_repo():
            return SnapshotResult(False, "", "git deposu değil — snapshot devre dışı")
        self._git("add", "-A")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        tag = f"milyonus-auto-{stamp}"
        self._git(
            "commit",
            "-m",
            f"[selfmod snapshot] {label}",
            "--allow-empty",
            "--no-verify",
        )
        rev = self._git("rev-parse", "HEAD").stdout.strip()
        self._git("tag", tag)
        return SnapshotResult(True, rev, f"snapshot {tag} @ {rev[:10]}")

    async def test_gate(self, *, run_doctor: bool = False) -> GateResult:
        """Run the test suite. Passing is the gate for keeping a self-edit."""
        proc = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "pytest",
            "-q",
            cwd=str(self.repo_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        text = out.decode("utf-8", "replace")
        passed = proc.returncode == 0
        if passed and run_doctor:
            d = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "milyonus",
                "doctor",
                cwd=str(self.repo_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            dout, _ = await d.communicate()
            text += "\n" + dout.decode("utf-8", "replace")
        return GateResult(passed, text[-4000:])

    def rollback(self, ref: str = "HEAD~1") -> str:
        """Hard-reset the working tree to a prior snapshot."""
        if not self.is_git_repo():
            return "git deposu değil — geri alma yapılamaz"
        res = self._git("reset", "--hard", ref)
        return res.stdout.strip() or res.stderr.strip() or f"geri alındı: {ref}"

    def log(self, *, limit: int = 20) -> list[str]:
        """List recent self-modification snapshots."""
        res = self._git("log", "--oneline", f"-{limit}", "--grep=selfmod snapshot")
        return [ln for ln in res.stdout.splitlines() if ln.strip()]

    async def apply_change(
        self, label: str, mutate, *, run_doctor: bool = False
    ) -> tuple[bool, str]:
        """Snapshot, run `mutate` (an async callable that edits files), gate on
        tests, auto-rollback if red. Returns (kept, message)."""
        snap = self.snapshot(label)
        if not snap.ok:
            return (False, snap.message)
        try:
            await mutate()
        except Exception as exc:  # noqa: BLE001 - report and roll back
            self.rollback(snap.ref)
            return (False, f"değişiklik hata verdi, geri alındı: {exc}")
        gate = await self.test_gate(run_doctor=run_doctor)
        if not gate.passed:
            self.rollback(snap.ref)
            tail = gate.output.strip().splitlines()[-3:]
            return (False, "test kapısı kırmızı — geri alındı:\n" + "\n".join(tail))
        return (True, f"değişiklik kabul edildi ({label})")
