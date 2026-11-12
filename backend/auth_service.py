"""Authentication business logic: users and sessions.

Framework-independent on purpose (no FastAPI imports): every function takes an open database
connection and an explicit `now` (epoch seconds), which keeps it easy to test and to reuse.
"""
from __future__ import annotations

import sqlite3

from config import Settings
from security import hash_password, hash_token, new_token, verify_password

TOUCH_INTERVAL_SECONDS = 60  # update last_seen_at at most once a minute
ROLES = ("SUPER_ADMIN", "OWNER", "MANAGER", "ACCOUNTANT")


def session_limits(settings: Settings, remember: bool) -> tuple[int, int]:
    """(absolute lifetime, idle limit) in seconds."""
    if remember:
        return settings.remember_days * 86_400, settings.remember_idle_days * 86_400
    return settings.session_hours * 3_600, settings.session_idle_minutes * 60


# ── Users ────────────────────────────────────────────────────────────────────
def create_user(conn: sqlite3.Connection, email: str, password: str, role: str, now: float) -> int:
    """Insert a user with an Argon2-hashed password. Raises sqlite3.IntegrityError if the email exists."""
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r}.")
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
        (email, hash_password(password), role, int(now)),
    )
    return int(cur.lastrowid)


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> sqlite3.Row | None:
    """Return the user row if email+password are correct and the account is active, else None.

    A password hash is verified even when the email is unknown, so timing does not reveal
    whether an account exists. Callers must show the same error for every failure.
    """
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    ok, needs_rehash = verify_password(user["password_hash"] if user else None, password)
    if user is None or not ok or not user["is_active"]:
        return None
    if needs_rehash:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user["id"]))
    return user


# ── Sessions ─────────────────────────────────────────────────────────────────
def create_session(conn: sqlite3.Connection, settings: Settings, user_id: int, remember: bool, now: float) -> str:
    """Create a session and return the RAW token (goes in the cookie). Only its hash is stored."""
    lifetime, _ = session_limits(settings, remember)
    raw = new_token()
    conn.execute(
        "INSERT INTO sessions (user_id, token_hash, created_at, last_seen_at, expires_at, remember) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, hash_token(raw), int(now), int(now), int(now) + lifetime, 1 if remember else 0),
    )
    conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (int(now), user_id))
    return raw


def resolve_session(conn: sqlite3.Connection, settings: Settings, raw_token: str, now: float) -> dict | None:
    """Return {user_id, email, role, remember, ...} for a valid session, else None.

    A session is invalid if unknown, revoked, past its absolute expiry, idle too long, or its user
    was deactivated. Expired sessions are revoked on the spot.
    """
    row = conn.execute(
        "SELECT s.id AS session_id, s.user_id, s.created_at, s.last_seen_at, s.expires_at, s.remember, "
        "       s.revoked_at, u.email, u.role, u.is_active "
        "FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
        (hash_token(raw_token),),
    ).fetchone()
    if row is None or row["revoked_at"] is not None:
        return None
    _, idle_limit = session_limits(settings, bool(row["remember"]))
    if now >= row["expires_at"] or now - row["last_seen_at"] > idle_limit or not row["is_active"]:
        conn.execute("UPDATE sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (int(now), row["session_id"]))
        return None
    if now - row["last_seen_at"] >= TOUCH_INTERVAL_SECONDS:
        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (int(now), row["session_id"]))
    return dict(row)


def revoke_session(conn: sqlite3.Connection, raw_token: str, now: float) -> None:
    conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
        (int(now), hash_token(raw_token)),
    )


def purge_sessions(conn: sqlite3.Connection, now: float) -> int:
    """Delete sessions that expired, or were revoked more than a day ago. Returns the number removed."""
    cur = conn.execute(
        "DELETE FROM sessions WHERE expires_at < ? OR (revoked_at IS NOT NULL AND revoked_at < ?)",
        (int(now), int(now) - 86_400),
    )
    return cur.rowcount
