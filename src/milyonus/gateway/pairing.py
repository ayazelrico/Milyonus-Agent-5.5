"""DM pairing — who is allowed to talk to the agent over a messaging channel.

Follows the OWASP/NIST-style guidance in PLAN §6 layer 2:
  - 8-char codes from an unambiguous alphabet (no 0/O/1/I), crypto-random.
  - Codes expire after 1 hour.
  - Request rate limit: 1 per 10 minutes per user.
  - Lockout: 5 failed attempts -> 1 hour lock.
  - Pairing state stored under ~/.milyonus/ with chmod 0600.
Default posture is deny: an unknown user is refused until paired (or explicitly
allowlisted by the operator).
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from milyonus.config.paths import data_root

# Unambiguous alphabet: no 0/O/1/I/L to avoid transcription errors.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_CODE_LEN = 8
_CODE_TTL = 3600.0
_REQUEST_INTERVAL = 600.0
_MAX_FAILURES = 5
_LOCKOUT = 3600.0


def _now() -> float:
    return time.time()


def generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))


@dataclass
class PendingCode:
    code: str
    channel: str
    created_at: float

    def expired(self, now: float | None = None) -> bool:
        return (now or _now()) - self.created_at > _CODE_TTL


@dataclass
class UserState:
    failures: int = 0
    locked_until: float = 0.0
    last_request: float = 0.0


@dataclass
class PairingState:
    # channel -> set of paired external user ids (stored as lists in JSON).
    paired: dict[str, list[str]] = field(default_factory=dict)
    pending: dict[str, dict] = field(default_factory=dict)  # code -> PendingCode
    users: dict[str, dict] = field(default_factory=dict)  # "chan:uid" -> UserState


class PairingManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (data_root() / "pairing.json")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> PairingState:
        if not self.path.exists():
            return PairingState()
        try:
            raw = json.loads(self.path.read_text("utf-8"))
            return PairingState(**raw)
        except (OSError, json.JSONDecodeError, TypeError):
            return PairingState()

    def _save(self) -> None:
        self.path.write_text(json.dumps(asdict(self._state), ensure_ascii=False))
        self.path.chmod(0o600)

    # --- operator side: create a code ----------------------------------

    def new_code(self, channel: str) -> str:
        code = generate_code()
        self._state.pending[code] = asdict(
            PendingCode(code=code, channel=channel, created_at=_now())
        )
        self._save()
        return code

    # --- user side: redeem a code --------------------------------------

    def _user(self, channel: str, uid: str) -> UserState:
        key = f"{channel}:{uid}"
        return UserState(**self._state.users.get(key, {}))

    def _store_user(self, channel: str, uid: str, u: UserState) -> None:
        self._state.users[f"{channel}:{uid}"] = asdict(u)

    def is_paired(self, channel: str, uid: str) -> bool:
        return uid in self._state.paired.get(channel, [])

    def redeem(self, channel: str, uid: str, code: str) -> tuple[bool, str]:
        """Attempt to pair. Returns (ok, message)."""
        now = _now()
        u = self._user(channel, uid)
        if u.locked_until > now:
            mins = int((u.locked_until - now) // 60) + 1
            return (False, f"too many failed attempts — locked for {mins} min")

        entry = self._state.pending.get(code.strip().upper())
        valid = (
            entry is not None
            and entry["channel"] == channel
            and not PendingCode(**entry).expired(now)
        )
        if not valid:
            u.failures += 1
            if u.failures >= _MAX_FAILURES:
                u.locked_until = now + _LOCKOUT
                u.failures = 0
            self._store_user(channel, uid, u)
            self._save()
            return (False, "invalid or expired code")

        # Success: pair and consume the code.
        self._state.paired.setdefault(channel, [])
        if uid not in self._state.paired[channel]:
            self._state.paired[channel].append(uid)
        del self._state.pending[code.strip().upper()]
        self._store_user(channel, uid, UserState())  # reset failures
        self._save()
        return (True, "pairing successful")

    def can_request(self, channel: str, uid: str) -> bool:
        """Rate-limit: at most one request per interval."""
        u = self._user(channel, uid)
        return _now() - u.last_request >= _REQUEST_INTERVAL

    def mark_request(self, channel: str, uid: str) -> None:
        u = self._user(channel, uid)
        u.last_request = _now()
        self._store_user(channel, uid, u)
        self._save()

    def unpair(self, channel: str, uid: str) -> None:
        if uid in self._state.paired.get(channel, []):
            self._state.paired[channel].remove(uid)
            self._save()
