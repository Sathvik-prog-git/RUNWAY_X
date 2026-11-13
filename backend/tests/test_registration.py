"""Registration rules + atomic database logic. Pure standard library (no FastAPI/Argon2 needed)."""
import sqlite3

import pytest

import registration as reg
from db import connection, init_db

GOOD = dict(full_name="Asha Rao", email="asha@acme.in", password_hash="$argon2id$placeholder",
            company_name="Acme Castings", phone="+919876543210", gstin=None, now=1_800_000_000)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "t.db")
    init_db(path)
    return path


def counts(path):
    with connection(path) as c:
        return (c.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM users").fetchone()[0])


@pytest.mark.parametrize("raw", [
    "9876543210", "98765 43210", "09876543210", "919876543210", "+919876543210",
    "+91 98765 43210", "+91-98765-43210", " (+91) 98765-43210 ", "6000000000",
])
def test_phone_is_normalised(raw):
    assert reg.normalize_indian_mobile(raw) == "+91" + "".join(ch for ch in raw if ch.isdigit())[-10:]


@pytest.mark.parametrize("raw", [
    "", "12345", "5876543210", "98765432", "98765432101", "+449876543210", "+9198765432",
    "abcdefghij", "+91 98765 4321x", "0919876543210", "٩٨٧٦٥٤٣٢١٠",
])
def test_bad_phone_is_rejected(raw):
    with pytest.raises(ValueError):
        reg.normalize_indian_mobile(raw)


def test_gstin_rules():
    assert reg.normalize_gstin(None) is None and reg.normalize_gstin("   ") is None
    assert reg.normalize_gstin(" 22aaaaa0000a1z5 ") == "22AAAAA0000A1Z5"
    for bad in ["22AAAAA0000A1Z", "00AAAAA0000A1Z5", "22AAAAA0000A1X5", "AAAAAAAAAAAAAAA", "22AAAAA0000A0Z5"]:
        with pytest.raises(ValueError):
            reg.normalize_gstin(bad)


def test_password_rules():
    assert reg.check_password("a-long-unusual-passphrase", "x@y.com") is None
    assert "at least" in reg.check_password("short", "x@y.com")
    assert reg.check_password("x" * 129)
    assert "email" in reg.check_password("someone@example.com", "someone@example.com")
    assert "common" in reg.check_password("password1234")
    assert "repetitive" in reg.check_password("abababababab")


def test_names_are_cleaned_and_checked():
    assert reg.normalize_full_name("  Asha   Rao ") == "Asha Rao"
    assert reg.normalize_company_name("  Acme  Castings Pvt. Ltd. ") == "Acme Castings Pvt. Ltd."
    for bad in ["", "A", "1234", "Bad\x00Name"]:
        with pytest.raises(ValueError):
            reg.normalize_full_name(bad)
    with pytest.raises(ValueError):
        reg.normalize_company_name("!!")


def test_registration_creates_company_and_owner_together(db):
    with connection(db) as c:
        user_id, company_id = reg.register_owner(c, **GOOD)
    with connection(db) as c:
        u = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        co = c.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    assert u["role"] == "OWNER" and u["company_id"] == company_id and u["phone"] == "+919876543210"
    assert u["full_name"] == "Asha Rao" and co["name"] == "Acme Castings" and co["gstin"] is None


def test_duplicate_email_is_atomic_and_case_insensitive(db):
    with connection(db) as c:
        reg.register_owner(c, **GOOD)
    with pytest.raises(reg.DuplicateEmail):
        with connection(db) as c:
            reg.register_owner(c, **{**GOOD, "email": "ASHA@acme.in", "company_name": "Other Co"})
    assert counts(db) == (1, 1)            # the second company was rolled back, not left without an owner


def test_duplicate_gstin_is_rejected_but_blank_gstin_repeats_are_fine(db):
    g = "22AAAAA0000A1Z5"
    with connection(db) as c:
        reg.register_owner(c, **{**GOOD, "gstin": g})
    with pytest.raises(reg.DuplicateGstin):
        with connection(db) as c:
            reg.register_owner(c, **{**GOOD, "email": "b@x.in", "gstin": g})
    assert counts(db) == (1, 1)
    with connection(db) as c:
        reg.register_owner(c, **{**GOOD, "email": "c@x.in"})
        reg.register_owner(c, **{**GOOD, "email": "d@x.in"})
    assert counts(db) == (3, 3)


def test_failure_after_company_insert_leaves_nothing_behind(db):
    with pytest.raises(sqlite3.IntegrityError):
        with connection(db) as c:
            reg.register_owner(c, **{**GOOD, "password_hash": None})   # NOT NULL violation on the user insert
    assert counts(db) == (0, 0)
