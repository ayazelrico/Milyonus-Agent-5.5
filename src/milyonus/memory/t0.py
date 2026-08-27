"""T0 write service — the authenticated, two-phase operator boundary (H1).

T0 (operator authority) can only be created out-of-band, bound to an Ed25519
signature, in two AND-layered phases:

  1. stage    — a signed claim lands passive (state=t0_staged); NOT a default.
  2. activate — requires a SECOND signature over "activate:<id>:<hash>" AND at
                least `t0_review_seconds` elapsed since staging. Only then is it
                an active default. A time window alone never activates T0.

No path from model-visible text reaches here — this service is called only by the
`milyonus admin` CLI, which is not exposed to the agent or any channel.
"""

from __future__ import annotations

import base64
import time

from milyonus.config.schema import MemoryConfig
from milyonus.memory.store import MemoryStore
from milyonus.security.operator import fingerprint, verify


class T0Error(Exception):
    """Raised when a T0 write fails authentication or the review gap."""


def stage_message(content: str) -> bytes:
    return content.encode("utf-8")


def activate_message(item_id: str, evidence_hash: str) -> bytes:
    return f"activate:{item_id}:{evidence_hash}".encode()


def stage_t0(store: MemoryStore, content: str, *, signature_b64: str) -> str:
    """Verify the operator signature over the content, then stage a T0 claim."""
    try:
        sig = base64.b64decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise T0Error("signature is not valid base64") from exc
    if not verify(stage_message(content), sig):
        raise T0Error(
            "operator signature invalid (or no operator key installed / "
            "cryptography missing) — T0 refused"
        )
    return store.stage_t0(content, signature=signature_b64, key_fingerprint=fingerprint())


def activate_t0(
    store: MemoryStore, item_id: str, *, signature_b64: str, config: MemoryConfig
) -> None:
    """Activate a staged T0 — requires the second signature AND the review gap."""
    item = store.get(item_id)
    if item is None or item.state != "t0_staged":
        raise T0Error(f"no staged T0 with id {item_id}")

    # AND-layer 1: mandatory review gap since staging.
    elapsed = time.time() - item.created_at
    if elapsed < config.t0_review_seconds:
        remaining = int(config.t0_review_seconds - elapsed)
        raise T0Error(
            f"review gap not elapsed — {remaining}s remaining before this T0 can be activated"
        )

    # AND-layer 2: a second, distinct signature over the activation message.
    try:
        sig = base64.b64decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise T0Error("activation signature is not valid base64") from exc
    if not verify(activate_message(item_id, item.evidence_hash), sig):
        raise T0Error("activation signature invalid — T0 not activated")

    store.activate_t0(item_id, signature=signature_b64)
