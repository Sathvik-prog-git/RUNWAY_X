"""Security primitives: Argon2 password hashing, session tokens, CSRF tokens, login throttling."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Callable

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # argon2-cffi defaults (Argon2id, RFC 9106 low-memory profile)
# Verified against when the email is unknown, so "no such user" costs the same time as "wrong password".
_DUMMY_HASH = _hasher.hash("runway-x-timing-equalizer")


# ── Passwords ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> tuple[bool, bool]:
    """Return (password_ok, needs_rehash). Pass stored_hash=None for an unknown user."""
    try:
        _hasher.verify(stored_hash or _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False, False
    if stored_hash is None:  # dummy hash matched: still not a real login
        return False, False
    return True, _hasher.check_needs_rehash(stored_hash)


# ── Session + CSRF tokens ────────────────────────────────────────────────────
def new_token() -> str:
    """Opaque session token: 256 bits from the OS CSPRNG."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Only this hash is stored. SHA-256 is appropriate because the token itself is high-entropy."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def csrf_token_for(raw_session_token: str, secret_key: str) -> str:
    """CSRF token bound to one session. The server can recompute it, so nothing extra is stored."""
    return hmac.new(secret_key.encode("utf-8"), b"csrf:" + raw_session_token.encode("utf-8"), hashlib.sha256).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# ── Login throttling (in-memory, per process) ────────────────────────────────
class LoginThrottle:
    """Allows `max_failures` failed logins per key within `window_seconds`, then blocks until the oldest expires."""

    def __init__(self, max_failures: int, window_seconds: int, clock: Callable[[], float] = time.time):
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._fails: dict[str, list[float]] = {}

    def _live(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._fails.get(key, []) if now - t < self._window]
        if recent:
            self._fails[key] = recent
        else:
            self._fails.pop(key, None)
        return recent

    def retry_after(self, key: str) -> int:
        """Seconds to wait before another attempt (0 = allowed)."""
        now = self._clock()
        recent = self._live(key, now)
        if len(recent) < self._max:
            return 0
        return max(1, int(self._window - (now - recent[0])) + 1)

    def record_failure(self, key: str) -> None:
        now = self._clock()
        if len(self._fails) > 10_000:  # keep memory bounded
            for k in list(self._fails):
                self._live(k, now)
        self._fails.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)
