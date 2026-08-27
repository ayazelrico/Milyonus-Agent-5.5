"""Automation suggestion — history-based, not foresight (design note part 1).

The honest mechanism: scan the session history for *repeated* user requests, and
when the same intent recurs, propose turning it into a scheduled task or a skill.
The system does not predict the future; it detects past repetition and offers a
rule. Suggestions are never auto-applied — the user must approve, because creating
a standing rule is a side-effectful change.
"""

from __future__ import annotations

from dataclasses import dataclass

from milyonus.core.store import SessionStore
from milyonus.memory.negative import jaccard


@dataclass(slots=True)
class Suggestion:
    kind: str  # "schedule" | "skill"
    intent: str  # a representative phrasing of the recurring request
    count: int  # how many times it was seen
    rationale: str

    def as_line(self) -> str:
        return f"[{self.kind}] seen {self.count}×: “{self.intent}” — {self.rationale}"


def _cluster(messages: list[str], threshold: float) -> list[tuple[str, int]]:
    """Group near-duplicate messages by lexical similarity; return
    (representative, count) for clusters, most frequent first."""
    clusters: list[list[str]] = []
    for msg in messages:
        placed = False
        for c in clusters:
            if jaccard(msg, c[0]) >= threshold:
                c.append(msg)
                placed = True
                break
        if not placed:
            clusters.append([msg])
    out = [(c[0], len(c)) for c in clusters]
    out.sort(key=lambda x: -x[1])
    return out


# Words that hint a request is time-recurring → suggest a schedule.
_RECURRING = ("every", "daily", "each", "morning", "günlük", "her", "weekly")


def suggest_automations(
    store: SessionStore,
    *,
    min_count: int = 3,
    similarity: float = 0.6,
    limit: int = 5,
) -> list[Suggestion]:
    """Return automation suggestions from repeated user requests."""
    # Read user messages directly across sessions.
    user_msgs: list[str] = []
    for session in store.list_sessions(limit=200):
        for m in store.history(session.id):
            if m["role"] == "user" and len(m["content"].strip()) > 8:
                user_msgs.append(m["content"].strip())

    suggestions: list[Suggestion] = []
    for rep, count in _cluster(user_msgs, similarity):
        if count < min_count:
            continue
        low = rep.lower()
        if any(w in low for w in _RECURRING):
            kind, why = "schedule", "recurring request — schedule it"
        else:
            kind, why = "skill", "repeated workflow — capture it as a skill"
        suggestions.append(Suggestion(kind=kind, intent=rep[:100], count=count, rationale=why))
        if len(suggestions) >= limit:
            break
    return suggestions
