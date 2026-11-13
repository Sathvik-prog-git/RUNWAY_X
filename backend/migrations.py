"""Versioned schema migrations for the SQLite database (standard library only).

Nothing here runs by itself. A migration is applied ONLY by the explicit command
`python migrate.py upgrade` (which backs the database up first), or on a brand-new empty database
file when it is first created (see db.init_db). An existing database is never changed on startup.

Every step checks the current state first, so running a migration again changes nothing.
The whole migration runs in one transaction: if any step fails, everything is rolled back.
"""
from __future__ import annotations

import sqlite3
import time

LATEST_VERSION = 1

TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    applied_at INTEGER NOT NULL
)
"""


class SchemaOutOfDateError(RuntimeError):
    """The database exists but has not been migrated to the schema this code needs."""


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def index_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone() is not None


def applied_versions(conn: sqlite3.Connection) -> set[int]:
    if not table_exists(conn, "schema_migrations"):
        return set()
    return {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}


def pending_versions(conn: sqlite3.Connection) -> list[int]:
    done = applied_versions(conn)
    return [v for v in range(1, LATEST_VERSION + 1) if v not in done]


# ── Migration 1: companies + registration fields on users ────────────────────
def _migration_1(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS companies ("
        " id         INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name       TEXT    NOT NULL,"
        " gstin      TEXT,"                     # NULL when not provided
        " created_at INTEGER NOT NULL,"
        " CHECK (gstin IS NULL OR length(gstin) = 15)"
        ")"
    )
    # Unique only for real values: any number of companies may have no GSTIN.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_gstin ON companies(gstin) "
        "WHERE gstin IS NOT NULL AND gstin <> ''"
    )
    existing = column_names(conn, "users")
    # Added as nullable columns: existing rows (e.g. the SUPER_ADMIN) keep every value they have.
    if "full_name" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "phone" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "company_id" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN company_id INTEGER REFERENCES companies(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")


MIGRATIONS = {1: ("companies_and_registration_fields", _migration_1)}


def upgrade(conn: sqlite3.Connection, now: float | None = None) -> list[int]:
    """Apply every pending migration inside ONE transaction. Returns the versions applied.

    The connection must be in autocommit mode (isolation_level=None) so the BEGIN/COMMIT below are
    the only transaction boundaries. Safe to call repeatedly.
    """
    if conn.in_transaction:
        raise RuntimeError("upgrade() needs a connection with no open transaction.")
    stamp = int(now if now is not None else time.time())
    applied: list[int] = []
    conn.execute("BEGIN IMMEDIATE")          # take the write lock up front
    try:
        conn.execute(TRACKING_TABLE_SQL)
        for version in pending_versions(conn):
            name, fn = MIGRATIONS[version]
            fn(conn)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, stamp),
            )
            applied.append(version)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return applied


def require_current(conn: sqlite3.Connection) -> None:
    """Raise SchemaOutOfDateError (with the exact command to run) unless the schema is up to date."""
    if pending_versions(conn):
        raise SchemaOutOfDateError(
            "The database schema is out of date. Stop the server, then run these commands in the backend folder:\n"
            "  python migrate.py rehearse    (tries the migration on a throw-away copy)\n"
            "  python migrate.py upgrade     (backs up first, then migrates)\n"
            "The server never changes an existing database on its own."
        )
