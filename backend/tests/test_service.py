"""Tests for the framework-independent logic: database, passwords, sessions, throttling, settings."""
import sqlite3
from dataclasses import replace

import pytest

import auth_service as svc
from config import Settings
from conftest import EMAIL, PASSWORD
from db import connection, init_db
from security import LoginThrottle, csrf_token_for, hash_token, new_token

T0 = 1_800_000_000  # fixed "now" so expiry maths is exact
HOUR, DAY = 3600, 86_400


@pytest.fixture
def db(settings):
    init_db(settings.database_path)
    return settings.database_path


@pytest.fixture
def user_id(db):
    with connection(db) as conn:
        return svc.create_user(conn, EMAIL, PASSWORD, "SUPER_ADMIN", T0)


# ── passwords / users ────────────────────────────────────────────────────────
def test_password_is_stored_hashed_not_plaintext(db, user_id):
    with connection(db) as conn:
        stored = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    assert "$argon2" in stored and PASSWORD not in stored


def test_authenticate_accepts_only_correct_credentials(db, user_id):
    with connection(db) as conn:
        assert svc.authenticate(conn, EMAIL, PASSWORD)["id"] == user_id
        assert svc.authenticate(conn, EMAIL, "wrong-password-123") is None
        assert svc.authenticate(conn, "nobody@example.com", PASSWORD) is None


def test_inactive_user_cannot_log_in(db, user_id):
    with connection(db) as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        assert svc.authenticate(conn, EMAIL, PASSWORD) is None


def test_duplicate_email_is_rejected_case_insensitively(db, user_id):
    with pytest.raises(sqlite3.IntegrityError):
        with connection(db) as conn:
            svc.create_user(conn, EMAIL.upper(), PASSWORD, "OWNER", T0)


def test_unknown_role_is_rejected(db):
    with pytest.raises(ValueError):
        with connection(db) as conn:
            svc.create_user(conn, "x@example.com", PASSWORD, "GOD", T0)


# ── sessions ─────────────────────────────────────────────────────────────────
def test_only_the_token_hash_is_stored(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, False, T0)
        rows = conn.execute("SELECT token_hash FROM sessions").fetchall()
        dump = " ".join(str(tuple(r)) for r in conn.execute("SELECT * FROM sessions").fetchall())
    assert len(rows) == 1 and rows[0][0] == hash_token(raw)
    assert raw not in dump and len(raw) >= 40


def test_tokens_are_unique_and_random():
    assert len({new_token() for _ in range(200)}) == 200


def test_valid_session_resolves_and_unknown_does_not(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, False, T0)
        info = svc.resolve_session(conn, settings, raw, T0 + 10)
        assert info["email"] == EMAIL and info["role"] == "SUPER_ADMIN"
        assert svc.resolve_session(conn, settings, "not-a-real-token", T0 + 10) is None


def test_revoked_session_is_rejected(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, False, T0)
        svc.revoke_session(conn, raw, T0 + 5)
        assert svc.resolve_session(conn, settings, raw, T0 + 6) is None


def test_normal_session_expires_after_absolute_lifetime(db, settings, user_id):
    s = replace(settings, session_hours=12, session_idle_minutes=100_000)  # isolate absolute expiry
    with connection(db) as conn:
        raw = svc.create_session(conn, s, user_id, False, T0)
        assert svc.resolve_session(conn, s, raw, T0 + 12 * HOUR - 1) is not None
        assert svc.resolve_session(conn, s, raw, T0 + 12 * HOUR) is None


def test_normal_session_expires_when_idle(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, False, T0)  # idle limit 120 min
        assert svc.resolve_session(conn, settings, raw, T0 + 119 * 60) is not None
    with connection(db) as conn:
        # last activity was at T0+119min, so +119min more is within the limit, +121min is not
        assert svc.resolve_session(conn, settings, raw, T0 + 119 * 60 + 119 * 60) is not None
        assert svc.resolve_session(conn, settings, raw, T0 + 119 * 60 + 119 * 60 + 121 * 60) is None


def test_remember_me_lasts_30_days_but_not_longer(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, True, T0)
        expires = conn.execute("SELECT expires_at FROM sessions").fetchone()[0]
    assert expires - T0 == 30 * DAY
    with connection(db) as conn:
        for day in range(1, 30):  # a visit every day keeps the idle limit (7 days) satisfied
            assert svc.resolve_session(conn, settings, raw, T0 + day * DAY) is not None
        assert svc.resolve_session(conn, settings, raw, T0 + 30 * DAY) is None


def test_remember_me_session_expires_after_7_idle_days(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, True, T0)
        assert svc.resolve_session(conn, settings, raw, T0 + 8 * DAY) is None


def test_deactivated_user_loses_existing_sessions(db, settings, user_id):
    with connection(db) as conn:
        raw = svc.create_session(conn, settings, user_id, False, T0)
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        assert svc.resolve_session(conn, settings, raw, T0 + 5) is None


def test_purge_removes_expired_sessions_only(db, settings, user_id):
    with connection(db) as conn:
        svc.create_session(conn, settings, user_id, False, T0)               # expires T0+12h
        svc.create_session(conn, settings, user_id, True, T0)                # expires T0+30d
        assert svc.purge_sessions(conn, T0 + 13 * HOUR) == 1
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


# ── csrf ─────────────────────────────────────────────────────────────────────
def test_csrf_token_is_stable_per_session_and_differs_between_sessions():
    a, b = new_token(), new_token()
    assert csrf_token_for(a, "k" * 40) == csrf_token_for(a, "k" * 40)
    assert csrf_token_for(a, "k" * 40) != csrf_token_for(b, "k" * 40)
    assert csrf_token_for(a, "k" * 40) != csrf_token_for(a, "j" * 40)


# ── throttle ─────────────────────────────────────────────────────────────────
def test_throttle_blocks_after_max_failures_and_recovers():
    now = [1000.0]
    th = LoginThrottle(max_failures=3, window_seconds=600, clock=lambda: now[0])
    for _ in range(3):
        assert th.retry_after("a") == 0
        th.record_failure("a")
    assert th.retry_after("a") > 0
    assert th.retry_after("b") == 0          # other keys unaffected
    now[0] += 601
    assert th.retry_after("a") == 0          # window passed


def test_throttle_reset_clears_failures():
    th = LoginThrottle(2, 600)
    th.record_failure("a"); th.record_failure("a")
    assert th.retry_after("a") > 0
    th.reset("a")
    assert th.retry_after("a") == 0


# ── settings ─────────────────────────────────────────────────────────────────
def test_settings_reject_missing_or_short_secret():
    with pytest.raises(ValueError):
        Settings(secret_key="", database_path="x").validate_for_server()
    with pytest.raises(ValueError):
        Settings(secret_key="short", database_path="x").validate_for_server()


def test_settings_reject_wildcard_origin_and_insecure_https(settings):
    with pytest.raises(ValueError):
        replace(settings, allowed_origins=("*",)).validate_for_server()
    with pytest.raises(ValueError):
        replace(settings, allowed_origins=("https://app.example.com",), cookie_secure=False).validate_for_server()
    replace(settings, allowed_origins=("https://app.example.com",), cookie_secure=True).validate_for_server()


def test_settings_accept_defaults(settings):
    settings.validate_for_server()
