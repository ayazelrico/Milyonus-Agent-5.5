"""Credential redaction for tool output and error messages (PLAN §6 layer 4).

Any text that flows back into the model — tool results, MCP errors — is scrubbed
of things that look like secrets, so a leaked key in an error string cannot be
learned or echoed. Also provides the env allowlist used when spawning subprocesses.
"""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
]

# Env vars always safe to pass to subprocesses; everything else is stripped.
_ENV_ALLOWLIST = {
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_ALL",
    "TERM",
    "SHELL",
    "TMPDIR",
}
_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH", re.IGNORECASE)


def redact(text: str) -> str:
    for pat in _PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def safe_env(base: dict[str, str], *, extra_allow: list[str] | None = None) -> dict[str, str]:
    """Filter an environment down to the allowlist + XDG_* + explicit extras.
    Names that look secret are always stripped even if explicitly allowed."""
    allow = set(_ENV_ALLOWLIST)
    allow.update(extra_allow or [])
    out: dict[str, str] = {}
    for k, v in base.items():
        if _SECRET_NAME.search(k) and k not in (extra_allow or []):
            continue
        if k in allow or k.startswith("XDG_"):
            out[k] = v
    return out
