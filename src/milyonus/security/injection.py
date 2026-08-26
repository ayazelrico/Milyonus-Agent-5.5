"""Prompt-injection / poisoning scanner.

Runs over any untrusted text before it can reach the system prompt or be promoted
to durable memory (PLAN §6 layer 5, §4.1). It is deliberately conservative: it
flags, it does not silently rewrite. A memory candidate that trips a high-severity
signal is never auto-promoted (PLAN §4.1 imperative scanner).

F2 ships the memory-critical signals; F4 broadens coverage (context files, web,
email) using the same Finding shape.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

Severity = Literal["low", "medium", "high"]


@dataclass(slots=True)
class Finding:
    signal: str
    severity: Severity
    detail: str


# Phrases that try to override prior instructions / assert authority.
_OVERRIDE = re.compile(
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all)\b"
    r"|\byou are now\b|\bfrom now on\b.{0,20}\byou (must|will|should)\b"
    r"|\b(system|developer|admin)\s*(prompt|message|override)\b"
    r"|önceki.{0,20}(talimat|komut).{0,20}(yok say|unut|görmezden)"
    r"|bundan (sonra|böyle).{0,20}(yapmalısın|zorundasın)"
    r"|sen (artık|şimdi|bundan (sonra|böyle)).{0,30}(asistan|ajan|model|bot)"
    r"|kısıtlama(sız| yok| olmadan)|sınırsız (asistan|ajan|model)",
    re.IGNORECASE | re.DOTALL,
)

# Imperative / tool-triggering shapes inappropriate for an "observation".
_IMPERATIVE = re.compile(
    r"\b(run|execute|delete|remove|send|email|curl|wget|download|upload|"
    r"install|forward|exfiltrate|chmod|rm\s+-rf|drop\s+table)\b"
    r"|\b(çalıştır|sil|kaldır|gönder|indir|kur|yükle|yolla|ilet|aktar)\b",
    re.IGNORECASE,
)

# Credential exfiltration / secret-reading shapes.
_CREDENTIAL = re.compile(
    r"\b(api[_-]?key|secret|token|password|credential|\.env|private[_-]?key)\b"
    r"|\bsk-[a-z0-9]{8,}|\bghp_[a-z0-9]{20,}|\bbearer\s+[a-z0-9._-]{16,}"
    r"|kimlik\s*bilgi|gizli\s*anahtar",
    re.IGNORECASE,
)

# Attempts to grant the agent authority or waive safeguards — the
# "policy-compliant looking" injection that reads like a benign statement.
_AUTHORITY = re.compile(
    r"onay\s*(istemeden|almadan)|onaysız|izin\s*(istemeden|almadan|vermeden)"
    r"|yetki\s*ver|kısıtlama.{0,15}(kaldır|yok say)"
    r"|without\s+(approval|permission|asking)|bypass.{0,15}(approval|safeguard|check)"
    r"|artık.{0,20}(yapmalı|çalıştırmalı|yüklemeli)"
    r"|(agent|ajan|asistan).{0,25}(onaysız|yapmalı|çalıştırmalı|zorunda)"
    r"|onay\s*isteme|(agent|ajan|asistan).{0,35}(oku|eriş|çalıştır|yükle|sil)(abilir|abilirsin|abilirsiniz|malı|meli)",
    re.IGNORECASE | re.DOTALL,
)


# Zero-width / bidi / invisible characters used to smuggle hidden instructions.
_INVISIBLE = {
    "​",
    "‌",
    "‍",
    "⁠",
    "﻿",
    "‪",
    "‫",
    "‬",
    "‭",
    "‮",
    "⁦",
    "⁧",
    "⁨",
    "⁩",
}


def _has_invisible(text: str) -> str | None:
    found = sorted({c for c in text if c in _INVISIBLE})
    if found:
        return " ".join(f"U+{ord(c):04X}" for c in found)
    # Also flag control chars other than tab/newline/carriage-return.
    for c in text:
        if unicodedata.category(c) == "Cc" and c not in "\t\n\r":
            return f"U+{ord(c):04X}"
    return None


def scan(text: str) -> list[Finding]:
    """Return all findings for a piece of untrusted text (empty == clean)."""
    findings: list[Finding] = []
    if _OVERRIDE.search(text):
        findings.append(Finding("instruction_override", "high", "instruction-override pattern"))
    if _IMPERATIVE.search(text):
        findings.append(
            Finding("imperative", "medium", "imperative/action inappropriate for an observation")
        )
    if _CREDENTIAL.search(text):
        findings.append(Finding("credential", "high", "credential/secret pattern"))
    if _AUTHORITY.search(text):
        findings.append(
            Finding("authority_grant", "high", "authority-grant / safeguard-bypass pattern")
        )
    inv = _has_invisible(text)
    if inv is not None:
        findings.append(Finding("invisible_unicode", "high", f"invisible character: {inv}"))
    return findings


def max_severity(findings: list[Finding]) -> Severity | None:
    order = {"low": 0, "medium": 1, "high": 2}
    if not findings:
        return None
    return max(findings, key=lambda f: order[f.severity]).severity


def is_safe_for_autopromote(findings: list[Finding]) -> bool:
    """A candidate may auto-promote only if nothing medium+ was found."""
    sev = max_severity(findings)
    return sev is None or sev == "low"
