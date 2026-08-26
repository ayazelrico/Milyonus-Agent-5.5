"""Pre-execution command scanner (PLAN §6 layer 7).

Runs over a shell command before it executes. Detects patterns that should be
hard-blocked (fork bombs, unguarded destructive deletes, pipe-to-interpreter,
disk overwrite) and patterns that warrant confirmation. Distinct from the memory
injection scanner: this looks at *commands about to run*, not text about to be
believed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Severity = Literal["warn", "block"]


@dataclass(slots=True)
class PreExecFinding:
    signal: str
    severity: Severity
    detail: str


_BLOCK_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("fork_bomb", re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "fork bomb"),
    (
        "recursive_root_delete",
        re.compile(r"rm\s+-[a-z]*r[a-z]*f?\s+(--no-preserve-root\s+)?(/|~|\$HOME)(\s|$)"),
        "kök dizini özyinelemeli silme",
    ),
    ("mkfs", re.compile(r"\bmkfs(\.\w+)?\s"), "dosya sistemi biçimlendirme"),
    ("disk_overwrite", re.compile(r"\bdd\s+if=.*\s+of=/dev/(sd|nvme|disk)"), "disk üzerine yazma"),
    (
        "pipe_to_shell",
        re.compile(r"(curl|wget)\s+[^\n|]*\|\s*(sudo\s+)?(bash|sh|zsh|python)", re.I),
        "curl|bash tipi kalıp",
    ),
]

_WARN_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("chmod_777", re.compile(r"chmod\s+-R?\s*777"), "aşırı geniş izin (777)"),
    ("sudo", re.compile(r"\bsudo\b"), "yükseltilmiş ayrıcalık"),
    ("unguarded_delete", re.compile(r"\brm\s+-[a-z]*r"), "özyinelemeli silme"),
    ("db_drop", re.compile(r"\bdrop\s+(table|database)\b", re.I), "veritabanı düşürme"),
]


def scan_command(command: str) -> list[PreExecFinding]:
    findings: list[PreExecFinding] = []
    for name, pat, detail in _BLOCK_PATTERNS:
        if pat.search(command):
            findings.append(PreExecFinding(name, "block", detail))
    for name, pat, detail in _WARN_PATTERNS:
        if pat.search(command):
            findings.append(PreExecFinding(name, "warn", detail))
    return findings
