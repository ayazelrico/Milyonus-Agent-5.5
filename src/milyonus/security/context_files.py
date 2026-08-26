"""Context-file scanning (PLAN §6 layer 5).

Agents commonly read repo context files (AGENTS.md, .cursorrules, CLAUDE.md,
SOUL.md, README) into their system prompt. Those files are untrusted: a poisoned
repo can plant "ignore your instructions / read .env / curl your keys" there.
This module loads such files, scans each with the injection scanner, and returns
only the clean ones as prompt sections — flagged files are dropped with a note
the operator can see, never silently injected.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from milyonus.security.injection import Finding, max_severity, scan

# Files an agent might pull into context, in priority order.
_CONTEXT_FILENAMES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    "SOUL.md",
    ".milyonusrules",
)


@dataclass(slots=True)
class ContextFileResult:
    path: Path
    included: bool
    findings: list[Finding]
    content: str


def scan_context_files(root: Path) -> list[ContextFileResult]:
    """Scan known context files under `root`. Included files are safe to inject."""
    results: list[ContextFileResult] = []
    for name in _CONTEXT_FILENAMES:
        p = root / name
        if not p.is_file():
            continue
        try:
            content = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
        findings = scan(content)
        sev = max_severity(findings)
        # High-severity content is dropped; low/medium is allowed but noted.
        included = sev != "high"
        results.append(ContextFileResult(p, included, findings, content))
    return results


def safe_context_sections(root: Path) -> tuple[list[str], list[ContextFileResult]]:
    """Return (prompt sections for clean files, all results incl. dropped ones)."""
    results = scan_context_files(root)
    sections = [
        f"# Project context: {r.path.name}\n{r.content.strip()}"
        for r in results
        if r.included and r.content.strip()
    ]
    return sections, results
