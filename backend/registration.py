"""Company registration rules and database logic (standard library only; no FastAPI/Pydantic here).

The browser's checks are only a convenience: everything is re-checked here, and the role and the
company are decided here — never taken from the request.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata

OWNER_ROLE = "OWNER"            # the ONLY role public registration can ever create
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

GSTIN_RE = re.compile(r"^(\d{2})[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
VALID_GST_STATE_CODES = {f"{n:02d}" for n in range(1, 39)} | {"97", "99"}

_COMMON_PASSWORDS = {
    "password1234", "password12345", "123456789012", "1234567890123", "qwertyuiop12", "qwerty123456",
    "iloveyou1234", "admin1234567", "welcome12345", "letmein12345", "passw0rd1234", "abc123456789",
    "123456123456", "111111111111", "000000000000", "password@123", "admin@123456", "india@123456",
}


class DuplicateEmail(Exception):
    """An account with this email already exists."""


class DuplicateGstin(Exception):
    """Another company already uses this GSTIN."""


def _has_control_chars(text: str) -> bool:
    return any(unicodedata.category(ch).startswith("C") for ch in text)


def _clean_text(raw: str) -> str:
    """Trim and collapse runs of whitespace."""
    return " ".join(raw.split())


def normalize_full_name(raw: str) -> str:
    name = _clean_text(raw)
    if _has_control_chars(name):
        raise ValueError("Full name contains characters that are not allowed.")
    if not 2 <= len(name) <= 100:
        raise ValueError("Enter your full name (2 to 100 characters).")
    if not any(ch.isalpha() for ch in name):
        raise ValueError("Enter your full name using letters.")
    return name


def normalize_company_name(raw: str) -> str:
    name = _clean_text(raw)
    if _has_control_chars(name):
        raise ValueError("Company name contains characters that are not allowed.")
    if not 2 <= len(name) <= 120:
        raise ValueError("Enter your company name (2 to 120 characters).")
    if not any(ch.isalnum() for ch in name):
        raise ValueError("Enter a valid company name.")
    return name


def normalize_indian_mobile(raw: str) -> str:
    """Accept 9876543210, 09876543210, 919876543210, +91 98765 43210, +91-98765-43210 … → +919876543210."""
    cleaned = re.sub(r"[\s\-().]", "", raw)
    plus = cleaned.startswith("+")
    digits = cleaned[1:] if plus else cleaned
    if not digits.isascii() or not digits.isdigit():
        raise ValueError("Enter a valid Indian mobile number, like 98765 43210.")
    if plus:
        if not (digits.startswith("91") and len(digits) == 12):
            raise ValueError("Enter a valid Indian mobile number, like +91 98765 43210.")
        digits = digits[2:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not (len(digits) == 10 and digits[0] in "6789"):
        raise ValueError("Enter a valid 10-digit Indian mobile number starting with 6, 7, 8 or 9.")
    return f"+91{digits}"


def normalize_gstin(raw: str | None) -> str | None:
    """Empty/blank → None (no GSTIN). Otherwise upper-case, check the 15-character structure and state code.

    The final check character is NOT verified (so valid-looking test numbers are accepted).
    """
    if raw is None:
        return None
    gstin = raw.strip().upper().replace(" ", "")
    if not gstin:
        return None
    match = GSTIN_RE.match(gstin)
    if not match or match.group(1) not in VALID_GST_STATE_CODES:
        raise ValueError("Enter a valid 15-character GSTIN, like 22AAAAA0000A1Z5, or leave it blank.")
    return gstin


def check_password(password: str, email: str = "", full_name: str = "") -> str | None:
    """Return a problem description, or None if the password is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    lowered = password.lower()
    local = email.split("@")[0].lower() if email else ""
    if email and (lowered == email.lower() or (local and lowered == local)):
        return "Password must not be the same as your email address."
    if full_name and lowered == full_name.strip().lower():
        return "Password must not be the same as your name."
    if lowered in _COMMON_PASSWORDS:
        return "This password is too common. Choose something less predictable."
    if len(set(password)) < 5:
        return "Password is too repetitive. Mix in more different characters."
    return None


def register_owner(
    conn: sqlite3.Connection,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    company_name: str,
    phone: str,
    gstin: str | None,
    now: float,
) -> tuple[int, int]:
    """Create the company and its OWNER user in ONE transaction. Returns (user_id, company_id).

    If either insert fails (duplicate email, duplicate GSTIN, any error) nothing is kept: no company
    is left behind without an owner. The caller's connection() context commits only on success.
    """
    try:
        company_id = conn.execute(
            "INSERT INTO companies (name, gstin, created_at) VALUES (?, ?, ?)",
            (company_name, gstin, int(now)),
        ).lastrowid
        user_id = conn.execute(
            "INSERT INTO users (email, password_hash, role, is_active, created_at, full_name, phone, company_id) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
            (email, password_hash, OWNER_ROLE, int(now), full_name, phone, company_id),
        ).lastrowid
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc)
        if "users.email" in message:
            raise DuplicateEmail from exc
        if "companies.gstin" in message:
            raise DuplicateGstin from exc
        raise
    return int(user_id), int(company_id)
