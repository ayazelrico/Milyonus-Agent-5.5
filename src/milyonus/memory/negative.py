"""Negative memory & rephrase detection (PLAN §4.4).

Closes Hermes's §9.4 gap: a rejected idea, resubmitted in different words, must
be recognized as the same idea. When embeddings are unavailable (the default,
no vec extra) we use a lexical similarity (token Jaccard over normalized words)
as a cheap, dependency-free first pass. The optional vec layer can raise recall
later, but the lexical pass already catches the common "reworded proposal" case.
"""

from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"\w+", re.UNICODE)
# Turkish + English stopwords that carry little discriminative signal.
_STOP = {
    "ve",
    "ile",
    "bir",
    "bu",
    "şu",
    "o",
    "için",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "is",
    "are",
    "in",
    "on",
    "da",
    "de",
    "ki",
    "mi",
    "her",
}


def _tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    return {t for t in _WORD.findall(text) if t not in _STOP and len(t) > 2}


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def is_rephrase(
    candidate: str, prior: list[str], *, threshold: float = 0.86
) -> tuple[bool, str | None, float]:
    """Return (is_rephrase, matched_prior, score). A candidate is a rephrase of a
    prior rejected idea if lexical similarity meets the threshold. The threshold
    default matches config.memory.rephrase_similarity."""
    best_score = 0.0
    best_match: str | None = None
    for p in prior:
        score = jaccard(candidate, p)
        if score > best_score:
            best_score, best_match = score, p
    return (best_score >= threshold, best_match, best_score)
