"""Backend settings, read from environment variables (and an optional backend/.env file).

Real environment variables always win over values in .env. Nothing secret is hardcoded:
SECRET_KEY must be supplied by you (see backend/.env.example).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
_ORIGIN_RE = re.compile(r"^https?://[^/\s*]+$")


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader (KEY=VALUE lines, # comments). Existing environment variables are kept."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_path: str
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    cookie_name: str = "rx_session"
    cookie_secure: bool = False          # set COOKIE_SECURE=true when served over HTTPS
    cookie_samesite: str = "lax"         # "lax" or "strict"
    session_hours: int = 12              # normal login: absolute lifetime
    session_idle_minutes: int = 120      # normal login: logged out after this much inactivity
    remember_days: int = 30              # "Remember me": absolute lifetime
    remember_idle_days: int = 7          # "Remember me": inactivity limit
    login_max_failures: int = 5          # failed attempts allowed per email+IP ...
    login_window_minutes: int = 15       # ... within this window

    def validate_for_server(self) -> None:
        """Raise ValueError with a clear message if the settings are unsafe or incomplete."""
        if len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY is missing or too short (need at least 32 characters). Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
                "and put it in backend/.env as SECRET_KEY=..."
            )
        if self.cookie_samesite not in ("lax", "strict"):
            raise ValueError("COOKIE_SAMESITE must be 'lax' or 'strict'.")
        if not self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS must list at least one origin.")
        for origin in self.allowed_origins:
            if not _ORIGIN_RE.match(origin):
                raise ValueError(f"Invalid origin {origin!r}: use e.g. http://localhost:5173 (no wildcard, no path).")
        if not self.cookie_secure and any(
            o.startswith("https://") for o in self.allowed_origins
        ):
            raise ValueError("COOKIE_SECURE must be true when ALLOWED_ORIGINS contains an https:// origin.")
        for name in ("session_hours", "session_idle_minutes", "remember_days", "remember_idle_days",
                     "login_max_failures", "login_window_minutes"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name.upper()} must be a positive number.")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{name} must be true or false.")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number.") from None


def load_settings() -> Settings:
    _load_dotenv(BACKEND_DIR / ".env")
    defaults = Settings(secret_key="", database_path="")
    db_path = Path(os.environ.get("DATABASE_PATH") or (BACKEND_DIR / "runway_dev.db"))
    if not db_path.is_absolute():
        db_path = BACKEND_DIR / db_path
    origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
    origins = tuple(o.strip().rstrip("/") for o in origins_raw.split(",") if o.strip()) or defaults.allowed_origins
    return Settings(
        secret_key=os.environ.get("SECRET_KEY", ""),
        database_path=str(db_path),
        allowed_origins=origins,
        cookie_name=os.environ.get("SESSION_COOKIE_NAME", defaults.cookie_name),
        cookie_secure=_env_bool("COOKIE_SECURE", defaults.cookie_secure),
        cookie_samesite=os.environ.get("COOKIE_SAMESITE", defaults.cookie_samesite).strip().lower(),
        session_hours=_env_int("SESSION_HOURS", defaults.session_hours),
        session_idle_minutes=_env_int("SESSION_IDLE_MINUTES", defaults.session_idle_minutes),
        remember_days=_env_int("REMEMBER_DAYS", defaults.remember_days),
        remember_idle_days=_env_int("REMEMBER_IDLE_DAYS", defaults.remember_idle_days),
        login_max_failures=_env_int("LOGIN_MAX_FAILURES", defaults.login_max_failures),
        login_window_minutes=_env_int("LOGIN_WINDOW_MINUTES", defaults.login_window_minutes),
    )
