"""Security scanner for skills (PLAN §5.5).

Every hub-loaded skill passes through this before it can be installed. It reuses
the injection scanner for prose and adds skill-specific signals: destructive
shell, pipe-to-interpreter, data exfiltration, and credential reads. The verdict
grades to caution/danger; `--force` may pass a caution but NEVER a danger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from milyonus.security.injection import scan as scan_prose

Verdict = Literal["clean", "caution", "danger"]

_DESTRUCTIVE = re.compile(
    r"rm\s+-rf\s+[/~]|mkfs|dd\s+if=|:\(\)\s*\{.*\};:|chmod\s+-R?\s*777\s+/"
    r"|>\s*/dev/sd|drop\s+table|truncate\s+table",
    re.IGNORECASE,
)
_PIPE_TO_SHELL = re.compile(
    r"(curl|wget)\s+[^\n|]*\|\s*(sudo\s+)?(bash|sh|zsh|python)", re.IGNORECASE
)
_EXFIL = re.compile(
    r"(curl|wget|nc|scp)\s+[^\n]*(\.env|id_rsa|/etc/passwd|credential|secret)"
    r"|base64\s+[^\n]*(\.env|id_rsa|key)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class SkillFinding:
    signal: str
    verdict: Verdict
    detail: str


def scan_skill(text: str) -> list[SkillFinding]:
    findings: list[SkillFinding] = []
    if _DESTRUCTIVE.search(text):
        findings.append(SkillFinding("destructive_command", "danger", "destructive command"))
    if _PIPE_TO_SHELL.search(text):
        findings.append(SkillFinding("pipe_to_interpreter", "danger", "curl|bash-style pattern"))
    if _EXFIL.search(text):
        findings.append(SkillFinding("exfiltration", "danger", "data-exfiltration pattern"))
    for f in scan_prose(text):
        v: Verdict = "danger" if f.severity == "high" else "caution"
        findings.append(SkillFinding(f"prose:{f.signal}", v, f.detail))
    return findings


def worst_verdict(findings: list[SkillFinding]) -> Verdict:
    if any(f.verdict == "danger" for f in findings):
        return "danger"
    if any(f.verdict == "caution" for f in findings):
        return "caution"
    return "clean"


def may_install(findings: list[SkillFinding], *, force: bool) -> bool:
    """danger is never installable; caution needs force; clean always installs."""
    v = worst_verdict(findings)
    if v == "danger":
        return False
    if v == "caution":
        return force
    return True
