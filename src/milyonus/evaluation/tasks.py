"""TaskBench — real tasks with programmatic success checks.

Each task gives the agent a workspace, a prompt, and a `check(workspace) -> bool`
that verifies the outcome deterministically (no LLM judge needed). This measures
whether the agent actually did the job — the question benchmarks like PoisonBench
can't answer.

Tasks use only the safe filesystem + shell tools so they run without network,
and the check inspects the resulting files.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Task:
    id: str
    prompt: str
    check: Callable[[Path], bool]
    setup: Callable[[Path], None] = lambda _p: None
    category: str = "general"
    files: dict[str, str] = field(default_factory=dict)  # written into the workspace


def _read(p: Path, rel: str) -> str:
    f = p / rel
    return f.read_text("utf-8") if f.exists() else ""


TASKS: list[Task] = [
    Task(
        id="create-file",
        category="fs",
        prompt="Create a file named hello.txt containing exactly the text: Merhaba Milyonus",
        check=lambda p: _read(p, "hello.txt").strip() == "Merhaba Milyonus",
    ),
    Task(
        id="read-and-answer",
        category="fs",
        prompt="Read secret.txt and write the secret word (only the word) into answer.txt.",
        files={"secret.txt": "The secret word is LACIVERT.\n"},
        check=lambda p: "LACIVERT" in _read(p, "answer.txt"),
    ),
    Task(
        id="count-lines",
        category="fs",
        prompt="data.txt has several lines. Write the number of lines into count.txt.",
        files={"data.txt": "a\nb\nc\nd\n"},
        check=lambda p: _read(p, "count.txt").strip().startswith("4"),
    ),
    Task(
        id="transform-json",
        category="data",
        prompt='input.json holds {"name": "ayaz"}. Write a file upper.txt with the '
        "name in uppercase.",
        files={"input.json": '{"name": "ayaz"}\n'},
        check=lambda p: "AYAZ" in _read(p, "upper.txt"),
    ),
    Task(
        id="rename-content",
        category="fs",
        prompt="notes.md contains the word 'draft'. Replace it with 'final' and save the file.",
        files={"notes.md": "# Report\nStatus: draft\n"},
        check=lambda p: "final" in _read(p, "notes.md") and "draft" not in _read(p, "notes.md"),
    ),
]
