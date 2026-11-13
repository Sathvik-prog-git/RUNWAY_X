"""Database access (SQLite for local development).

All SQL lives in db.py and auth_service.py, and every function receives a connection, so moving to
PostgreSQL later means swapping this module's connect()/init_db() and adjusting a few SQL details
(placeholders and AUTOINCREMENT) — routes and business logic stay the same.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import migrations

# Base (version 0) schema. Newer tables/columns (companies, registration fields) come from migrations.py.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    INTEGER NOT NULL,
    last_login_at INTEGER
);

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT    NOT NULL UNIQUE,   -- SHA-256 of the cookie token; the raw token is never stored
    created_at   INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    expires_at   INTEGER NOT NULL,          -- absolute expiry (epoch seconds, UTC)
    remember     INTEGER NOT NULL DEFAULT 0,
    revoked_at   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection(path: str) -> Iterator[sqlite3.Connection]:
    """Short-lived connection: commits on success, rolls back on error, always closes."""
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _readonly_connection(path: str) -> sqlite3.Connection:
    """A connection that cannot write: used to inspect an existing database without touching it."""
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)


def _is_new_database(path: str) -> bool:
    """True only for a missing file, a zero-byte file, or a database with no tables at all."""
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return True
    conn = _readonly_connection(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    finally:
        conn.close()


def init_db(path: str) -> None:
    """Prepare the database file.

    * Brand-new database (no file, empty file, or no tables): create the base tables, bring them to the
      latest schema and switch it to WAL mode. This is the only case where anything is written.
    * Existing database: inspected through a READ-ONLY connection, so nothing in it is modified — no
      tables, no data and no journal mode. If a migration is still pending this raises
      SchemaOutOfDateError, telling you to run `python migrate.py upgrade` explicitly.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if _is_new_database(path):
        conn = sqlite3.connect(path, timeout=10, isolation_level=None)  # autocommit: migrations manage their own transaction
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
            migrations.upgrade(conn)
        finally:
            conn.close()
        return
    conn = _readonly_connection(path)
    try:
        if not migrations.table_exists(conn, "users"):
            raise migrations.SchemaOutOfDateError(
                "This database file has tables but no 'users' table, so it does not look like a RUNWAY X database. "
                "It was left untouched. Check DATABASE_PATH in backend/.env."
            )
        migrations.require_current(conn)
    finally:
        conn.close()
