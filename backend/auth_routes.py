"""HTTP endpoints: POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout.

Session model: an opaque random token lives in an HttpOnly cookie; only its SHA-256 hash is in the
database. State-changing requests are protected by (1) the Origin allow-list check in main.py,
(2) SameSite cookies, and (3) a per-session CSRF token sent in the X-CSRF-Token header.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from auth_service import authenticate, create_session, purge_sessions, resolve_session, revoke_session
from config import Settings
from db import connection
from schemas import LoginRequest
from security import csrf_token_for, tokens_match

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_LOGIN_ERROR = "Incorrect email or password."


def _set_session_cookie(response: Response, settings: Settings, raw_token: str, remember: bool) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        max_age=settings.remember_days * 86_400 if remember else None,  # None = browser-session cookie
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name, path="/", httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite
    )


def _raw_cookie(request: Request, settings: Settings) -> str | None:
    raw = request.cookies.get(settings.cookie_name)
    return raw if raw and len(raw) <= 200 else None


def current_session(request: Request) -> tuple[str, dict] | None:
    """(raw_token, session_info) for a valid session cookie, else None."""
    settings: Settings = request.app.state.settings
    raw = _raw_cookie(request, settings)
    if raw is None:
        return None
    with connection(settings.database_path) as conn:
        info = resolve_session(conn, settings, raw, request.app.state.clock())
    return (raw, info) if info else None


def require_user(request: Request) -> dict:
    """Dependency for future private endpoints: Depends(require_user) → 401 unless signed in."""
    found = current_session(request)
    if found is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return found[1]


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    settings: Settings = request.app.state.settings
    throttle = request.app.state.throttle
    now = request.app.state.clock()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{body.email}|{client_ip}"

    wait = throttle.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many failed sign-in attempts. Please wait a few minutes and try again.",
            headers={"Retry-After": str(wait)},
        )

    with connection(settings.database_path) as conn:
        user = authenticate(conn, body.email, body.password)
        if user is None:
            throttle.record_failure(key)
            raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)  # same for unknown email / bad password / disabled
        throttle.reset(key)
        old = _raw_cookie(request, settings)
        if old:
            revoke_session(conn, old, now)  # never reuse or keep a previous session
        purge_sessions(conn, now)
        raw = create_session(conn, settings, user["id"], body.remember, now)

    _set_session_cookie(response, settings, raw, body.remember)
    return {
        "user": {"id": user["id"], "email": user["email"], "role": user["role"]},
        "csrfToken": csrf_token_for(raw, settings.secret_key),
    }


@router.get("/me")
def me(request: Request):
    settings: Settings = request.app.state.settings
    found = current_session(request)
    if found is None:
        resp = JSONResponse({"detail": "Not authenticated."}, status_code=401)
        if request.cookies.get(settings.cookie_name):
            _clear_session_cookie(resp, settings)  # drop a stale/invalid cookie
        return resp
    raw, info = found
    return {
        "user": {"id": info["user_id"], "email": info["email"], "role": info["role"]},
        "csrfToken": csrf_token_for(raw, settings.secret_key),
    }


@router.post("/logout")
def logout(request: Request):
    settings: Settings = request.app.state.settings
    now = request.app.state.clock()
    found = current_session(request)
    if found is not None:
        raw, _info = found
        supplied = request.headers.get("x-csrf-token", "")
        if not supplied or not tokens_match(supplied, csrf_token_for(raw, settings.secret_key)):
            raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")
        with connection(settings.database_path) as conn:
            revoke_session(conn, raw, now)
    resp = Response(status_code=204)  # idempotent: signing out when already signed out is fine
    _clear_session_cookie(resp, settings)
    return resp
