"""Migration + backup tests. Pure standard library (no FastAPI/Argon2 needed)."""
import hashlib
import shutil
import sqlite3
from pathlib import Path

import pytest

import migrate
import migrations
from db import SCHEMA, init_db

ADMIN_HASH = "$argon2id$v=19$m=65536,t=3,p=4$fake$fakehash"  # placeholder text; never verified here


def make_legacy_db(path: Path, wal: bool = True) -> sqlite3.Connection:
    """A database exactly as it was before registration existed (base schema, WAL mode, real rows).

    Returns an OPEN connection: while it stays open the newest rows live only in the -wal file.
    """
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO users (email, password_hash, role, is_active, created_at, last_login_at) VALUES (?,?,?,?,?,?)",
        ("admin@example.com", ADMIN_HASH, "SUPER_ADMIN", 1, 1_800_000_000, 1_800_000_500),
    )
    conn.execute(
        "INSERT INTO sessions (user_id, token_hash, created_at, last_seen_at, expires_at, remember) VALUES (1,'h1',1,1,99,0)"
    )
    conn.commit()
    return conn


def rows(path: Path, sql: str):
    c = sqlite3.connect(str(path))
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_new_empty_database_gets_latest_schema(tmp_path):
    db = tmp_path / "fresh.db"
    init_db(str(db))
    c = sqlite3.connect(str(db))
    assert migrations.pending_versions(c) == []
    assert {"full_name", "phone", "company_id"} <= migrations.column_names(c, "users")
    assert migrations.table_exists(c, "companies")
    c.close()


def test_existing_old_database_is_not_changed_on_startup(tmp_path):
    db = tmp_path / "old.db"
    keep = make_legacy_db(db)
    with pytest.raises(migrations.SchemaOutOfDateError) as err:
        init_db(str(db))
    assert "migrate.py upgrade" in str(err.value)
    assert not migrations.table_exists(keep, "companies")
    assert "company_id" not in migrations.column_names(keep, "users")
    keep.close()


def test_upgrade_preserves_super_admin_and_all_data_and_is_rerunnable(tmp_path):
    db = tmp_path / "old.db"
    keep = make_legacy_db(db)
    before = rows(db, "SELECT * FROM users")
    sessions_before = rows(db, "SELECT * FROM sessions")
    keep.close()

    assert migrate.main(["upgrade", "--db", str(db), "--backup-dir", str(tmp_path / "bk"), "--yes"]) == 0
    after = rows(db, "SELECT id,email,password_hash,role,is_active,created_at,last_login_at FROM users")
    assert after == [r for r in before]                      # old columns identical
    assert rows(db, "SELECT full_name, phone, company_id FROM users") == [(None, None, None)]
    assert rows(db, "SELECT * FROM sessions") == sessions_before
    assert rows(db, "SELECT version FROM schema_migrations") == [(1,)]
    assert len(list((tmp_path / "bk").glob("*.db"))) == 1

    # second run: nothing to do, no new backup, nothing changes
    assert migrate.main(["upgrade", "--db", str(db), "--backup-dir", str(tmp_path / "bk"), "--yes"]) == 0
    assert len(list((tmp_path / "bk").glob("*.db"))) == 1
    conn = sqlite3.connect(str(db), isolation_level=None)
    assert migrations.upgrade(conn) == []                    # calling the function directly is also a no-op
    conn.close()
    init_db(str(db))                                          # and the server's startup check now passes


def test_failed_migration_rolls_back_completely(tmp_path):
    db = tmp_path / "old.db"
    keep = make_legacy_db(db)
    original = migrations.MIGRATIONS[1]

    def broken(conn):
        original[1](conn)                                     # do the real work first ...
        raise RuntimeError("boom")                            # ... then fail

    migrations.MIGRATIONS[1] = (original[0], broken)
    try:
        conn = sqlite3.connect(str(db), isolation_level=None)
        with pytest.raises(RuntimeError):
            migrations.upgrade(conn)
        conn.close()
    finally:
        migrations.MIGRATIONS[1] = original
    assert not migrations.table_exists(keep, "companies")
    assert "full_name" not in migrations.column_names(keep, "users")
    assert not migrations.table_exists(keep, "schema_migrations")
    assert keep.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    keep.close()


def test_backup_contains_changes_that_only_exist_in_the_wal_file(tmp_path):
    db = tmp_path / "wal.db"
    keep = make_legacy_db(db)                                 # connection stays open => rows are in -wal
    keep.execute("INSERT INTO users (email,password_hash,role,is_active,created_at) VALUES ('b@x.com','h','OWNER',1,2)")
    keep.commit()
    assert Path(str(db) + "-wal").exists()
    backup = migrate.backup_database(db, tmp_path / "bk")
    assert backup.suffix == ".db" and backup.parent == tmp_path / "bk"
    assert rows(backup, "SELECT email FROM users ORDER BY id") == [("admin@example.com",), ("b@x.com",)]
    assert rows(backup, "PRAGMA integrity_check") == [("ok",)]
    assert rows(backup, "PRAGMA journal_mode") == [("delete",)]   # single self-contained file
    keep.close()


def test_backup_refuses_missing_database_and_creates_nothing(tmp_path):
    missing = tmp_path / "nope.db"
    assert migrate.main(["backup", "--db", str(missing), "--backup-dir", str(tmp_path / "bk")]) == 1
    assert not missing.exists() and not (tmp_path / "bk").exists()


def test_rehearsal_passes_and_leaves_the_real_database_untouched(tmp_path):
    db = tmp_path / "old.db"
    keep = make_legacy_db(db)
    keep.close()
    before = rows(db, "SELECT * FROM users")
    assert migrate.main(["rehearse", "--db", str(db)]) == 0
    assert rows(db, "SELECT * FROM users") == before
    c = sqlite3.connect(str(db))
    assert migrations.pending_versions(c) == [1]              # still un-migrated
    assert not migrations.table_exists(c, "companies")
    c.close()


def test_gstin_unique_only_for_non_empty_values(tmp_path):
    db = tmp_path / "fresh.db"
    init_db(str(db))
    c = sqlite3.connect(str(db))
    c.execute("INSERT INTO companies (name, gstin, created_at) VALUES ('A', NULL, 1)")
    c.execute("INSERT INTO companies (name, gstin, created_at) VALUES ('B', NULL, 1)")   # many blanks are fine
    c.execute("INSERT INTO companies (name, gstin, created_at) VALUES ('C', '22AAAAA0000A1Z5', 1)")
    with pytest.raises(sqlite3.IntegrityError) as err:
        c.execute("INSERT INTO companies (name, gstin, created_at) VALUES ('D', '22AAAAA0000A1Z5', 1)")
    assert "companies.gstin" in str(err.value)
    c.close()


# ═════════════════════════════════════════════════════════════════════════════
# Regression tests for the three migration-safety fixes
# ═════════════════════════════════════════════════════════════════════════════
BLOB = bytes(range(256)) + b"\x00\xff\x00"


def add_business_data(conn: sqlite3.Connection) -> None:
    """Extra pre-existing tables (stand-ins for Transactions / Cash Flow data) with every SQLite type,
    an index, a trigger, a view, an AUTOINCREMENT counter and a WITHOUT ROWID table."""
    conn.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT NOT NULL UNIQUE, amount REAL, qty INTEGER,
            note TEXT, scan BLOB, customer_id INTEGER REFERENCES customers(id));
        CREATE INDEX idx_invoices_amount ON invoices(amount);
        CREATE TABLE ledger_kv (k TEXT PRIMARY KEY, v) WITHOUT ROWID;
        CREATE TRIGGER trg_noop AFTER INSERT ON customers BEGIN SELECT 1; END;
        CREATE VIEW v_big AS SELECT id FROM invoices WHERE amount > 1000;
        """
    )
    conn.executemany("INSERT INTO customers (id, name) VALUES (?, ?)", [(1, "Acme ₹ ünï"), (2, ""), (3, None)])
    conn.executemany(
        "INSERT INTO invoices (number, amount, qty, note, scan, customer_id) VALUES (?,?,?,?,?,?)",
        [
            ("INV-1", 1234.5, 2**62, "₹ ünï\nline2", BLOB, 1),
            ("INV-2", 0.1, -7, "", b"", 2),
            ("INV-3", None, None, None, None, None),
            ("INV-4", -0.0, 0, "x" * 5000, b"\x00", 3),
        ],
    )
    conn.executemany("INSERT INTO ledger_kv (k, v) VALUES (?, ?)", [("a", 1), ("b", 1.0), ("c", "1"), ("d", b"1"), ("e", None)])
    conn.commit()


def upgraded(tmp_path: Path, name: str, wal: bool = True):
    """Build legacy+business DB, run the real `migrate.py upgrade`, return (db_path, backup_path)."""
    d = tmp_path / name
    d.mkdir()
    db = d / "old.db"
    conn = make_legacy_db(db, wal=wal)
    add_business_data(conn)
    conn.close()
    assert migrate.main(["upgrade", "--db", str(db), "--backup-dir", str(d / "bk"), "--yes"]) == 0
    (backup,) = (d / "bk").glob("*.db")
    return db, backup


def snapshot_of(path: Path) -> dict:
    c = migrate.open_db(path, readonly=True)
    try:
        return migrate.database_snapshot(c)
    finally:
        c.close()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Issue 1: backup verification compares real data ──────────────────────────
def test_digest_distinguishes_storage_types_and_ignores_row_order(tmp_path):
    def digest(values):
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE t (v)")
        c.executemany("INSERT INTO t (v) VALUES (?)", [(v,) for v in values])
        return migrate.table_digest(c, "t", ["v"])

    variants = [[1], [1.0], ["1"], [b"1"], [None], ["abc"], [b"abc"], [""], [b""]]
    digests = [digest(v) for v in variants]
    assert len(set(digests)) == len(variants)                      # every storage class / value is distinct
    assert digest([1, "a", b"b"]) == digest([b"b", 1, "a"])        # order does not matter
    assert digest([1, 1]) != digest([1])                           # duplicates count


def test_backup_matches_source_for_every_table_including_blobs_and_wal_data(tmp_path):
    db = tmp_path / "src.db"
    keep = make_legacy_db(db)
    add_business_data(keep)
    keep.execute("INSERT INTO invoices (number, amount, scan) VALUES ('WAL-ONLY', 9.5, ?)", (BLOB[::-1],))
    keep.commit()                                                   # committed, still only in the -wal file
    assert Path(str(db) + "-wal").stat().st_size > 0
    backup = migrate.backup_database(db, tmp_path / "bk")
    assert migrate.snapshot_differences(snapshot_of(db), snapshot_of(backup)) == []
    assert rows(backup, "SELECT scan FROM invoices WHERE number = 'WAL-ONLY'") == [(BLOB[::-1],)]
    assert rows(backup, "SELECT scan FROM invoices WHERE number = 'INV-1'") == [(BLOB,)]
    assert rows(backup, "SELECT COUNT(*) FROM ledger_kv") == [(5,)]
    keep.close()


def test_snapshot_detects_a_single_changed_blob_byte_or_value(tmp_path):
    db = tmp_path / "src.db"
    c = make_legacy_db(db)
    add_business_data(c)
    c.close()
    backup = migrate.backup_database(db, tmp_path / "bk")
    base = snapshot_of(backup)
    for i, sql in enumerate([
        "UPDATE invoices SET scan = substr(scan, 1, 10) || x'ff' || substr(scan, 12) WHERE number = 'INV-1'",
        "UPDATE invoices SET amount = 1234.5000001 WHERE number = 'INV-1'",
        "UPDATE customers SET name = 'Acme ₹ unï' WHERE id = 1",
        "UPDATE ledger_kv SET v = 1 WHERE k = 'b'",           # 1.0 -> 1 (REAL -> INTEGER)
        "UPDATE ledger_kv SET v = x'31' WHERE k = 'c'",       # '1' -> x'31' (TEXT -> BLOB)
    ]):
        tampered = tmp_path / f"tampered{i}.db"
        shutil.copy2(backup, tampered)
        c = sqlite3.connect(str(tampered))
        c.execute(sql)
        c.commit()
        c.close()
        assert migrate.snapshot_differences(base, snapshot_of(tampered)), sql


def test_backup_is_deleted_and_rejected_if_the_copy_does_not_match(tmp_path):
    db = tmp_path / "src.db"
    c = make_legacy_db(db)
    add_business_data(c)
    c.close()
    real = migrate.database_snapshot
    calls = []

    def flaky(conn):
        snap = real(conn)
        calls.append(1)
        if len(calls) == 2:                                        # 2nd call = the copy: corrupt one table's digest
            snap["tables"]["invoices"] = (4, "0" * 64)
        return snap

    migrate.database_snapshot = flaky
    try:
        with pytest.raises(migrate.MigrationError) as err:
            migrate.backup_database(db, tmp_path / "bk")
    finally:
        migrate.database_snapshot = real
    assert "invoices" in str(err.value)
    assert list((tmp_path / "bk").glob("*.db")) == []              # the bad backup was removed


# ── Issue 2: post-migration verification covers every pre-existing table ─────
def test_upgrade_keeps_every_business_table_byte_for_byte(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    db = d / "old.db"
    c = make_legacy_db(db)
    add_business_data(c)
    c.close()
    before = snapshot_of(db)
    assert migrate.main(["upgrade", "--db", str(db), "--backup-dir", str(d / "bk"), "--yes"]) == 0
    after = snapshot_of(db)
    for table in ("customers", "invoices", "ledger_kv", "sessions", "sqlite_sequence"):
        assert after["tables"][table] == before["tables"][table], table
    c = migrate.open_db(db, readonly=True)
    original_user_columns = [r[1] for r in migrate.table_info(c, "users") if r[1] not in migrate.ADDED_USER_COLUMNS]
    assert migrate.table_digest(c, "users", original_user_columns) == before["tables"]["users"]
    c.close()
    names = {r[0] for r in rows(db, "SELECT name FROM sqlite_master")}
    assert {"idx_invoices_amount", "trg_noop", "v_big", "invoices", "customers", "ledger_kv"} <= names
    assert rows(db, "SELECT COUNT(*) FROM invoices") == [(4,)] and rows(db, "SELECT scan FROM invoices WHERE number='INV-1'") == [(BLOB,)]
    (backup,) = (d / "bk").glob("*.db")
    assert migrate.verify_upgrade(backup, db) == []


@pytest.mark.parametrize("tamper,expected", [
    ("UPDATE invoices SET amount = amount + 1 WHERE number = 'INV-2'", "'invoices': existing data changed"),
    ("UPDATE invoices SET scan = zeroblob(259) WHERE number = 'INV-1'", "'invoices': existing data changed"),
    ("UPDATE invoices SET qty = 4611686018427387903 WHERE number = 'INV-1'", "'invoices': existing data changed"),
    ("DELETE FROM customers WHERE id = 1", "'customers': row count changed"),
    ("INSERT INTO customers (id, name) VALUES (99, 'extra')", "'customers': row count changed"),
    ("UPDATE ledger_kv SET v = 2 WHERE k = 'a'", "'ledger_kv': existing data changed"),
    ("UPDATE ledger_kv SET v = 1 WHERE k = 'b'", "'ledger_kv': existing data changed"),
    ("ALTER TABLE invoices ADD COLUMN extra TEXT", "'invoices': columns/schema changed"),
    ("DROP INDEX idx_invoices_amount", "index 'idx_invoices_amount' is missing"),
    ("DROP VIEW v_big", "view 'v_big' is missing"),
    ("DROP TRIGGER trg_noop", "trigger 'trg_noop' is missing"),
    ("DROP TABLE ledger_kv", "table 'ledger_kv' is missing"),
    ("UPDATE users SET password_hash = 'tampered'", "'users': existing data changed"),
    ("UPDATE users SET full_name = 'x'", "users.full_name is not empty"),
    ("UPDATE sessions SET revoked_at = 5", "'sessions': existing data changed"),
    ("DELETE FROM sessions", "'sessions': row count changed"),
    ("UPDATE sqlite_sequence SET seq = seq + 5 WHERE name = 'invoices'", "'invoices': AUTOINCREMENT counter changed"),
])
def test_verify_upgrade_detects_changes_in_any_pre_existing_table(tmp_path, tamper, expected):
    db, backup = upgraded(tmp_path, "t")
    assert migrate.verify_upgrade(backup, db) == []
    c = sqlite3.connect(str(db))
    c.execute(tamper)
    c.commit()
    c.close()
    problems = migrate.verify_upgrade(backup, db)
    assert any(expected in p for p in problems), (tamper, problems)


# ── Issue 3: startup must not modify an existing database ────────────────────
def journal_mode(path: Path) -> str:
    return rows(path, "PRAGMA journal_mode")[0][0]


def test_startup_does_not_change_journal_mode_or_bytes_of_an_existing_rollback_journal_db(tmp_path):
    db = tmp_path / "legacy.db"
    make_legacy_db(db, wal=False).close()
    assert journal_mode(db) == "delete"
    before = file_sha(db)
    with pytest.raises(migrations.SchemaOutOfDateError) as err:
        init_db(str(db))
    assert "migrate.py upgrade" in str(err.value)
    assert journal_mode(db) == "delete"                      # NOT switched to WAL
    assert file_sha(db) == before                            # not a single byte changed
    assert sorted(p.name for p in tmp_path.iterdir()) == ["legacy.db"]   # no -wal/-shm/-journal left behind


def test_startup_leaves_an_existing_wal_database_untouched(tmp_path):
    db = tmp_path / "legacy.db"
    make_legacy_db(db, wal=True).close()
    before = file_sha(db)
    with pytest.raises(migrations.SchemaOutOfDateError):
        init_db(str(db))
    assert file_sha(db) == before and journal_mode(db) == "wal"
    c = sqlite3.connect(str(db))
    assert not migrations.table_exists(c, "companies") and "company_id" not in migrations.column_names(c, "users")
    c.close()


def test_startup_check_on_an_up_to_date_database_changes_nothing(tmp_path):
    db, _backup = upgraded(tmp_path, "u", wal=False)         # explicit migration keeps the rollback-journal mode
    assert journal_mode(db) == "delete"
    before = file_sha(db)
    init_db(str(db))                                          # passes: schema is current
    assert file_sha(db) == before and journal_mode(db) == "delete"


def test_startup_refuses_to_adopt_a_database_that_has_no_users_table(tmp_path):
    db = tmp_path / "other.db"
    c = sqlite3.connect(str(db))
    c.execute("CREATE TABLE something_else (x)")
    c.execute("INSERT INTO something_else VALUES (1)")
    c.commit()
    c.close()
    before = file_sha(db)
    with pytest.raises(migrations.SchemaOutOfDateError):
        init_db(str(db))
    assert file_sha(db) == before
    c = sqlite3.connect(str(db))
    assert not migrations.table_exists(c, "users") and not migrations.table_exists(c, "companies")
    c.close()


def test_genuinely_new_database_is_created_in_wal_mode(tmp_path):
    for name, prepare in (("missing.db", None), ("zero.db", b"")):
        db = tmp_path / name
        if prepare is not None:
            db.write_bytes(prepare)
        init_db(str(db))
        assert journal_mode(db) == "wal"
        c = sqlite3.connect(str(db))
        assert migrations.pending_versions(c) == [] and migrations.table_exists(c, "users")
        c.close()


def test_status_and_rehearse_do_not_modify_the_real_database(tmp_path):
    db = tmp_path / "legacy.db"
    make_legacy_db(db, wal=False).close()
    before = file_sha(db)
    assert migrate.main(["status", "--db", str(db)]) == 0
    assert migrate.main(["rehearse", "--db", str(db)]) == 0
    assert file_sha(db) == before and journal_mode(db) == "delete"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["legacy.db"]
