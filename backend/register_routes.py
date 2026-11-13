"""HTTP endpoint: POST /api/auth/register — create a company and its OWNER account, then sign the owner in.

Security notes
* The role is always OWNER and the company is always brand new; neither can come from the request
  (RegisterRequest forbids unknown fields, so `role`, `company_id`, … get a 422).
* The same Origin allow-list check as every other POST runs in main.py before this code.
* A duplicate email gets one generic message; the password is hashed BEFORE the database is touched,
  so "email already used" and "success" take about the same time.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from auth_routes import _raw_cookie, _set_session_cookie
from auth_service import create_session, purge_sessions, revoke_session
from config import Settings
from db import connection
from registration import DuplicateEmail, DuplicateGstin, register_owner
from schemas import RegisterRequest
from security import csrf_token_for, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_DUPLICATE_ERROR = (
    "We couldn't create an account with these details. If you already registered, try signing in instead."
)
GSTIN_TAKEN_ERROR = "This GSTIN is already registered. Check the number, or leave it blank."


@router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request, response: Response):
    settings: Settings = request.app.state.settings
    throttle = request.app.state.register_throttle
    now = request.app.state.clock()
    client_ip = request.client.host if request.client else "unknown"

    wait = throttle.retry_after(client_ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please wait a while and try again.",
            headers={"Retry-After": str(wait)},
        )
    throttle.record_failure(client_ip)   # every attempt counts, successful or not

    password_hash = hash_password(body.password)   # slow on purpose; done before taking the database write lock
    try:
        with connection(settings.database_path) as conn:
            user_id, _company_id = register_owner(
                conn,
                full_name=body.full_name,
                email=body.email,
                password_hash=password_hash,
                company_name=body.company_name,
                phone=body.phone,
                gstin=body.gstin,
                now=now,
            )
            old = _raw_cookie(request, settings)
            if old:
                revoke_session(conn, old, now)   # never keep a previous session
            purge_sessions(conn, now)
            raw = create_session(conn, settings, user_id, False, now)
    except DuplicateEmail:
        raise HTTPException(status_code=409, detail=GENERIC_DUPLICATE_ERROR) from None
    except DuplicateGstin:
        raise HTTPException(status_code=409, detail=GSTIN_TAKEN_ERROR) from None

    _set_session_cookie(response, settings, raw, False)
    return {
        "user": {"id": user_id, "email": body.email, "role": "OWNER"},
        "csrfToken": csrf_token_for(raw, settings.secret_key),
    }
