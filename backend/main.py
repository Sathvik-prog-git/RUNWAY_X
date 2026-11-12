"""RUNWAY X API entrypoint.

Run from the backend folder:  uvicorn main:app --reload --port 8000

Implemented: authentication (/api/auth/login, /api/auth/me, /api/auth/logout).
Still to come: /api/dashboard, /api/transactions, /api/simulate, /api/interventions.
"""
from __future__ import annotations

import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth_routes import router as auth_router
from config import Settings, load_settings
from db import init_db
from security import LoginThrottle

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_of(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.validate_for_server()
    init_db(settings.database_path)

    app = FastAPI(title="RUNWAY X API")
    app.state.settings = settings
    app.state.clock = time.time  # replaced in tests to simulate time passing
    app.state.throttle = LoginThrottle(
        settings.login_max_failures, settings.login_window_minutes * 60, clock=lambda: app.state.clock()
    )
    allowed = set(settings.allowed_origins)

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        """CSRF defence: state-changing requests must come from an allowed origin."""
        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin") or _origin_of(request.headers.get("referer"))
            if origin not in allowed:
                return JSONResponse({"detail": "Request origin not allowed."}, status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/auth"):
            response.headers["Cache-Control"] = "no-store"
        return response

    # Added after the guard, so CORS is the outermost layer.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    app.include_router(auth_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


_app: FastAPI | None = None


def __getattr__(name: str):
    """`uvicorn main:app` builds the app on first access, so merely importing this module
    (e.g. from the tests) needs no SECRET_KEY and creates no database."""
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
