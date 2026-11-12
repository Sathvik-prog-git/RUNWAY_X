"""Create the first administrator account from the command line (local use only).

    python create_admin.py --email you@example.com

The password is typed at a hidden prompt (never passed as an argument, so it does not end up in
shell history), hashed with Argon2, and stored in the database. There is no public endpoint for
this, and no default credentials exist.
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
import time

from auth_service import ROLES, create_user
from config import load_settings
from db import connection, init_db
from schemas import normalize_email

MIN_PASSWORD_LENGTH = 12


def check_password(password: str, email: str) -> str | None:
    """Return a problem description, or None if the password is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > 1024:
        return "Password is too long (max 1024 characters)."
    if password.lower() == email or password.lower() == email.split("@")[0]:
        return "Password must not be the same as the email address."
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an administrator account for RUNWAY X.")
    parser.add_argument("--email", required=True, help="login email for the new account")
    parser.add_argument("--role", default="SUPER_ADMIN", choices=ROLES, help="default: SUPER_ADMIN")
    args = parser.parse_args(argv)

    try:
        email = normalize_email(args.email)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    password = getpass.getpass("Password (hidden): ")
    if getpass.getpass("Repeat password: ") != password:
        print("Error: the two passwords do not match.", file=sys.stderr)
        return 2
    problem = check_password(password, email)
    if problem:
        print(f"Error: {problem}", file=sys.stderr)
        return 2

    settings = load_settings()
    init_db(settings.database_path)
    try:
        with connection(settings.database_path) as conn:
            user_id = create_user(conn, email, password, args.role, time.time())
    except sqlite3.IntegrityError:
        print(f"Error: an account for {email} already exists.", file=sys.stderr)
        return 1

    print(f"Created {args.role} account #{user_id} for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
