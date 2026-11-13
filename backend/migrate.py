"""Explicit database migration command (never run automatically).

    python migrate.py status                 show what is applied / pending
    python migrate.py backup                 make a verified backup copy and stop
    python migrate.py rehearse               try the migration on a throw-away COPY; the real database is untouched
    python migrate.py upgrade                back up, ask for confirmation, then migrate the real database

Options: --db PATH (default: DATABASE_PATH from backend/.env, else backend/runway_dev.db)
         --backup-dir DIR (default: backend/backups)      --yes (upgrade only: skip the confirmation prompt)

Backups use SQLite's online backup API, which reads the WAL file too, so the copy contains every
committed change even while the database is in WAL mode. Every backup is verified by comparing the
complete schema and the complete data of every table (byte for byte) with the source. After an
upgrade, every table that existed before is compared with the backup again. Stop the backend before
`upgrade` anyway.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import struct
import sys
import tempfile
import time
from pathlib import Path

import migrations
from config import BACKEND_DIR, load_settings

DEFAULT_BACKUP_DIR = BACKEND_DIR / "backups"


class MigrationError(RuntimeError):
    pass


ADDED_USER_COLUMNS = {"full_name", "phone", "company_id"}   # the only users columns migration 1 adds


def open_db(path: Path, *, must_exist: bool = True, readonly: bool = False) -> sqlite3.Connection:
    """Open the database. readonly=True opens it with mode=ro, so the connection cannot change anything."""
    if must_exist and not path.is_file():
        raise MigrationError(f"Database file not found: {path}\nNothing was created or changed.")
    if readonly:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30, isolation_level=None)
    else:
        conn = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _qi(name: str) -> str:
    """Quote an SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def table_names(conn: sqlite3.Connection, *, include_internal: bool = False) -> list[str]:
    where = "type = 'table'" + ("" if include_internal else " AND name NOT LIKE 'sqlite_%'")
    return [r[0] for r in conn.execute(f"SELECT name FROM sqlite_master WHERE {where} ORDER BY name")]


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {n: conn.execute(f"SELECT COUNT(*) FROM {_qi(n)}").fetchone()[0] for n in table_names(conn)}


def table_info(conn: sqlite3.Connection, table: str) -> list[tuple]:
    return [tuple(r) for r in conn.execute(f"PRAGMA table_info({_qi(table)})")]


def _encode_value(sqlite_type: str, value) -> bytes:
    """Exact, unambiguous bytes for one SQLite value: the storage class is part of the encoding,
    so 1, 1.0, '1' and x'31' all differ, and BLOBs/invalid-UTF-8 text are compared byte for byte."""
    if value is None:
        return b"N"
    if sqlite_type == "integer":
        return b"I" + str(int(value)).encode("ascii")
    if sqlite_type == "real":
        return b"R" + struct.pack(">d", value)
    if sqlite_type == "text":
        return b"T" + bytes(value)      # raw bytes as stored (connection uses text_factory=bytes)
    return b"B" + bytes(value)          # blob


def table_digest(conn: sqlite3.Connection, table: str, columns: list[str]) -> tuple[int, str]:
    """(row_count, sha256) of the given columns of every row.

    Each row is hashed on its own and the row hashes are sorted before combining, so the result does
    not depend on row order or on rowid/primary-key layout (works for WITHOUT ROWID tables too).
    """
    select = ", ".join(f"typeof({_qi(c)}), {_qi(c)}" for c in columns)
    row_hashes: list[bytes] = []
    previous = conn.text_factory
    conn.text_factory = bytes
    try:
        for row in conn.execute(f"SELECT {select} FROM {_qi(table)}"):
            h = hashlib.sha256()
            for i in range(0, len(row), 2):
                encoded = _encode_value(row[i].decode("ascii"), row[i + 1])
                h.update(len(encoded).to_bytes(8, "big"))
                h.update(encoded)
            row_hashes.append(h.digest())
    finally:
        conn.text_factory = previous
    row_hashes.sort()
    total = hashlib.sha256()
    for digest in row_hashes:
        total.update(digest)
    return len(row_hashes), total.hexdigest()


def database_snapshot(conn: sqlite3.Connection) -> dict:
    """Complete schema + complete data (every table, incl. sqlite_sequence) read in ONE read transaction."""
    conn.execute("BEGIN")
    try:
        schema = [tuple(r) for r in conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name")]
        tables = {}
        for name in table_names(conn, include_internal=True):
            cols = [r[1] for r in table_info(conn, name)]
            tables[name] = table_digest(conn, name, cols)
        return {"schema": schema, "tables": tables}
    finally:
        conn.execute("COMMIT")


def snapshot_differences(a: dict, b: dict) -> list[str]:
    diffs = []
    if a["schema"] != b["schema"]:
        diffs.append("schema (tables/indexes/triggers/views)")
    for name in sorted(set(a["tables"]) | set(b["tables"])):
        if a["tables"].get(name) != b["tables"].get(name):
            diffs.append(f"data of table '{name}'")
    return diffs


def backup_database(src: Path, backup_dir: Path, label: str = "pre-migration") -> Path:
    """Create <backup_dir>/<name>_<timestamp>_<label>.db via SQLite's backup API and verify it.

    Verification compares the complete schema and the complete contents of EVERY table (values and
    BLOBs, byte for byte) between the source and the copy, plus PRAGMA integrity_check on the copy.
    The source is opened read-only, so taking a backup cannot modify the database.
    """
    if not src.is_file():
        raise MigrationError(f"Database file not found: {src}\nNothing was created or changed.")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"{src.stem}_{stamp}_{label}.db"
    if dest.exists():
        raise MigrationError(f"Backup file already exists, refusing to overwrite: {dest}")
    source = open_db(src, readonly=True)
    try:
        target = sqlite3.connect(str(dest))
        try:
            source.backup(target)                      # consistent snapshot, includes committed WAL content
            target.execute("PRAGMA journal_mode = DELETE")  # make the backup one self-contained file
        finally:
            target.close()
        check = open_db(dest, readonly=True)
        try:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise MigrationError(f"Backup failed its integrity check ({result}). Removed: {dest}")
            diffs = snapshot_differences(database_snapshot(source), database_snapshot(check))
            if diffs:
                raise MigrationError(
                    "The backup does not match the database (" + "; ".join(diffs) + "). "
                    "The backup was deleted. If the backend is running, stop it and try again."
                )
        except MigrationError:
            check.close()
            dest.unlink(missing_ok=True)
            raise
        check.close()
    finally:
        source.close()
    return dest


def _sequences(conn: sqlite3.Connection) -> dict[str, int]:
    if "sqlite_sequence" not in table_names(conn, include_internal=True):
        return {}
    return {r[0]: r[1] for r in conn.execute("SELECT name, seq FROM sqlite_sequence")}


def verify_upgrade(before: Path, after: Path) -> list[str]:
    """Compare a pre-migration copy with the migrated database. Returns a list of problems (empty = good).

    Every table that existed before is checked: same columns/schema and an identical set of rows
    (values and BLOBs byte for byte). For `users` only the new columns are excluded from the comparison.
    Indexes, triggers and views that existed before must still exist unchanged.
    """
    problems: list[str] = []
    b, a = open_db(before, readonly=True), open_db(after, readonly=True)
    try:
        if a.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            problems.append("integrity_check failed after migration")
        if a.execute("PRAGMA foreign_key_check").fetchall():
            problems.append("foreign_key_check reported problems")
        if migrations.pending_versions(a):
            problems.append("migrations still pending after upgrade")

        before_tables = table_names(b)
        after_tables = set(table_names(a))
        seq_b, seq_a = _sequences(b), _sequences(a)
        for table in before_tables:
            if table == "schema_migrations":        # our own bookkeeping: earlier versions must still be recorded
                missing = migrations.applied_versions(b) - migrations.applied_versions(a)
                if missing:
                    problems.append(f"schema_migrations lost version(s) {sorted(missing)}")
                continue
            if table not in after_tables:
                problems.append(f"table '{table}' is missing after migration")
                continue
            info_b, info_a = table_info(b, table), table_info(a, table)
            if table == "users":
                if info_a[: len(info_b)] != info_b:
                    problems.append("users: original columns changed")
                compare_cols = [r[1] for r in info_b if r[1] not in ADDED_USER_COLUMNS]
            else:
                if info_a != info_b:
                    problems.append(f"'{table}': columns/schema changed")
                sql_b = b.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
                sql_a = a.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
                if sql_a != sql_b:
                    problems.append(f"'{table}': CREATE TABLE definition changed")
                if [tuple(r) for r in b.execute(f"PRAGMA foreign_key_list({_qi(table)})")] != [
                    tuple(r) for r in a.execute(f"PRAGMA foreign_key_list({_qi(table)})")
                ]:
                    problems.append(f"'{table}': foreign keys changed")
                compare_cols = [r[1] for r in info_b]
            count_b, digest_b = table_digest(b, table, compare_cols)
            count_a, digest_a = table_digest(a, table, compare_cols)
            if count_b != count_a:
                problems.append(f"'{table}': row count changed ({count_b} -> {count_a})")
            elif digest_b != digest_a:
                problems.append(f"'{table}': existing data changed")
            if seq_b.get(table) != seq_a.get(table):
                problems.append(f"'{table}': AUTOINCREMENT counter changed")

        # Pre-existing indexes / triggers / views must be untouched.
        sql_objects = lambda c: {(r[0], r[1], r[2], r[3]) for r in c.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type IN ('index','trigger','view')")}
        for obj in sorted(sql_objects(b) - sql_objects(a), key=str):
            problems.append(f"{obj[0]} '{obj[1]}' is missing or was changed")

        # Existing users must not have received values in the new columns.
        if "users" in before_tables:
            new_cols = ADDED_USER_COLUMNS - {r[1] for r in table_info(b, "users")}
            if new_cols:
                for col in sorted(new_cols):
                    if col not in {r[1] for r in table_info(a, "users")}:
                        problems.append(f"users.{col} is missing")
                    elif a.execute(f"SELECT COUNT(*) FROM users WHERE {_qi(col)} IS NOT NULL").fetchone()[0]:
                        problems.append(f"users.{col} is not empty for existing users")
        if "companies" not in after_tables:
            problems.append("companies table is missing")
        sa_before = b.execute("SELECT COUNT(*) FROM users WHERE role = 'SUPER_ADMIN'").fetchone()[0]
        sa_after = a.execute("SELECT COUNT(*) FROM users WHERE role = 'SUPER_ADMIN'").fetchone()[0]
        if sa_before != sa_after:
            problems.append("SUPER_ADMIN account count changed")
    finally:
        b.close()
        a.close()
    return problems


def run_upgrade(path: Path) -> list[int]:
    conn = open_db(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        return migrations.upgrade(conn)
    finally:
        conn.close()


# ── Commands ─────────────────────────────────────────────────────────────────
def cmd_status(path: Path, _args) -> int:
    conn = open_db(path, readonly=True)
    try:
        counts = table_counts(conn)
        pending = migrations.pending_versions(conn)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    print(f"Database : {path}\nJournal  : {mode}\nTables   : {counts}")
    print("Schema   : up to date" if not pending else f"Schema   : migration(s) pending: {pending}")
    return 0


def cmd_backup(path: Path, args) -> int:
    dest = backup_database(path, args.backup_dir)
    print(f"Backup created and verified: {dest}")
    return 0


def cmd_rehearse(path: Path, args) -> int:
    """Migrate a COPY, verify it, and run the migration a second time to prove it is safe to repeat."""
    with tempfile.TemporaryDirectory(prefix="runwayx_rehearsal_") as tmp:
        snapshot = backup_database(path, Path(tmp), label="snapshot")
        trial = Path(tmp) / "trial_copy.db"
        shutil.copy2(snapshot, trial)
        first = run_upgrade(trial)
        problems = verify_upgrade(snapshot, trial)
        second = run_upgrade(trial)
        if second:
            problems.append(f"re-running applied migrations again: {second}")
        problems += verify_upgrade(snapshot, trial)
    print(f"Rehearsal on a copy of: {path}")
    print(f"  first run applied    : {first or 'nothing (already up to date)'}")
    print(f"  second run applied   : {second or 'nothing (safe to repeat)'}")
    if problems:
        print("REHEARSAL FAILED:")
        for p in sorted(set(problems)):
            print(f"  - {p}")
        print("The real database was not touched. Do NOT run `upgrade`.")
        return 1
    print("  every existing table identical (data + schema), SUPER_ADMIN preserved, integrity + foreign keys OK")
    print("REHEARSAL PASSED. The real database was not touched.")
    return 0


def cmd_upgrade(path: Path, args) -> int:
    conn = open_db(path, readonly=True)
    try:
        if not migrations.pending_versions(conn):
            print("Nothing to do: the database is already up to date. (No backup made, nothing changed.)")
            return 0
    finally:
        conn.close()
    if not args.yes:
        print(f"This will migrate: {path}\nA verified backup is made first.")
        if input("Type YES to continue: ").strip() != "YES":
            print("Cancelled. Nothing was changed.")
            return 1
    backup = backup_database(path, args.backup_dir)
    print(f"Backup created and verified: {backup}")
    try:
        applied = run_upgrade(path)
    except Exception as exc:  # the migration itself is one transaction, so a failure leaves the database as it was
        print(f"Migration FAILED and was rolled back automatically: {exc}\nYour backup is still at: {backup}")
        return 1
    problems = verify_upgrade(backup, path)
    if problems:
        print("Migration finished but verification found problems:")
        for p in problems:
            print(f"  - {p}")
        print(f"Restore from the backup if needed: {backup}")
        return 1
    print(f"Migration applied: {applied}. Verification passed (every pre-existing table identical, SUPER_ADMIN preserved).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicit RUNWAY X database migrations.")
    parser.add_argument("command", choices=["status", "backup", "rehearse", "upgrade"])
    parser.add_argument("--db", type=Path, help="database file (default: DATABASE_PATH from .env)")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--yes", action="store_true", help="upgrade: do not ask for confirmation")
    args = parser.parse_args(argv)
    path = (args.db or Path(load_settings().database_path)).resolve()
    commands = {"status": cmd_status, "backup": cmd_backup, "rehearse": cmd_rehearse, "upgrade": cmd_upgrade}
    try:
        return commands[args.command](path, args)
    except MigrationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
