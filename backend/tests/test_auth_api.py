"""End-to-end tests of /api/auth/* through the real FastAPI app (needs fastapi + httpx installed)."""
import time
from dataclasses import replace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import auth_service as svc  # noqa: E402
from conftest import EMAIL, ORIGIN, PASSWORD  # noqa: E402
from db import connection  # noqa: E402
from main import create_app  # noqa: E402

HOUR, DAY = 3600, 86_400
WRONG = "definitely-not-the-password"


@pytest.fixture
def app(settings):
    app = create_app(settings)
    clock = {"now": time.time()}
    app.state.clock = lambda: clock["now"]
    app.state.fake_clock = clock
    with connection(settings.database_path) as conn:
        svc.create_user(conn, EMAIL, PASSWORD, "SUPER_ADMIN", clock["now"])
    return app


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost:5173") as c:
        c.headers["Origin"] = ORIGIN
        yield c


def advance(app, seconds):
    app.state.fake_clock["now"] += seconds


def cookie_attrs(set_cookie: str) -> set:
    """Attributes that must be identical when a cookie is set and when it is cleared (value/expiry excluded)."""
    parts = [p.strip().lower() for p in set_cookie.split(";")]
    return {p for p in parts[1:] if not p.startswith(("max-age", "expires"))}


def login(client, email=EMAIL, password=PASSWORD, remember=False):
    return client.post("/api/auth/login", json={"email": email, "password": password, "remember": remember})


# 1. valid credentials
def test_login_with_valid_credentials(client, settings):
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == EMAIL and body["user"]["role"] == "SUPER_ADMIN" and body["csrfToken"]
    assert "password" not in r.text.lower()
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert "max-age" not in cookie            # normal login = browser-session cookie
    assert "secure" not in cookie             # COOKIE_SECURE is false in local development
    assert r.headers["cache-control"] == "no-store"
    raw = client.cookies.get("rx_session")
    with connection(settings.database_path) as conn:   # raw token must not be in the database
        dump = str([tuple(row) for row in conn.execute("SELECT * FROM sessions")])
    assert raw and raw not in dump


# 2. + 3. + 4. bad credentials
def test_wrong_password_and_unknown_email_get_identical_generic_errors(client):
    wrong = login(client, password=WRONG)
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Incorrect email or password."}
    assert "set-cookie" not in wrong.headers


def test_invalid_email_is_rejected(client):
    assert login(client, email="not-an-email").status_code == 422


def test_empty_fields_are_rejected(client):
    assert login(client, email="", password="").status_code == 422
    assert login(client, password="").status_code == 422
    assert client.post("/api/auth/login", json={}).status_code == 422


# 5. + 6. protected access
def test_me_requires_authentication_then_works_after_login(client):
    assert client.get("/api/auth/me").status_code == 401
    login(client)
    r = client.get("/api/auth/me")
    assert r.status_code == 200 and r.json()["user"]["email"] == EMAIL


# 7. refresh: a brand-new request carrying only the cookie restores the session
def test_session_survives_browser_refresh(app):
    with TestClient(app, base_url="http://localhost:5173") as first:
        first.headers["Origin"] = ORIGIN
        login(first)
        cookie = first.cookies.get("rx_session")
    with TestClient(app, base_url="http://localhost:5173", cookies={"rx_session": cookie}) as second:
        assert second.get("/api/auth/me").status_code == 200


# 8. logout
def test_logout_revokes_session_and_requires_csrf_token(client, settings):
    csrf = login(client).json()["csrfToken"]
    assert client.post("/api/auth/logout").status_code == 403                                  # no CSRF header
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.get("/api/auth/me").status_code == 200                                       # still signed in
    token = client.cookies.get("rx_session")
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    # the old cookie value is dead even if an attacker kept a copy
    with TestClient(client.app, base_url="http://localhost:5173", cookies={"rx_session": token}) as stolen:
        assert stolen.get("/api/auth/me").status_code == 401
    with connection(settings.database_path) as conn:
        assert conn.execute("SELECT revoked_at FROM sessions").fetchone()[0] is not None


def test_logout_when_not_signed_in_is_harmless(client):
    assert client.post("/api/auth/logout").status_code == 204


# 9. remember me
def test_remember_me_sets_persistent_cookie_and_lasts_30_days(app, client):
    r = login(client, remember=True)
    assert f"max-age={30 * DAY}" in r.headers["set-cookie"].lower()
    advance(app, 6 * DAY)
    assert client.get("/api/auth/me").status_code == 200
    advance(app, 6 * DAY)
    assert client.get("/api/auth/me").status_code == 200
    advance(app, 31 * DAY)
    assert client.get("/api/auth/me").status_code == 401


# 10. expiry + invalid sessions
def test_normal_session_expires_by_inactivity_and_absolute_time(app, client):
    login(client)
    advance(app, 3 * HOUR)                       # idle limit is 2 hours
    assert client.get("/api/auth/me").status_code == 401
    login(client)
    for _ in range(14):                          # stays active, but 12h absolute limit still applies
        advance(app, HOUR)
        client.get("/api/auth/me")
    assert client.get("/api/auth/me").status_code == 401


def test_invalid_cookie_is_rejected_and_cleared(client):
    # No domain: Python's cookie jar would treat domain="localhost" as "localhost.local" and never send it.
    client.cookies.set("rx_session", "garbage-token-value")
    r = client.get("/api/auth/me")
    assert "rx_session=garbage-token-value" in r.request.headers["cookie"]   # the cookie really reached the server
    assert r.status_code == 401
    assert "max-age=0" in r.headers["set-cookie"].lower()


def test_expired_session_cookie_is_cleared_with_the_same_attributes(app, client):
    set_header = login(client).headers["set-cookie"]
    advance(app, 3 * HOUR)                                   # past the 2-hour idle limit
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    cleared = r.headers["set-cookie"]
    assert cleared.lower().startswith("rx_session=") and "max-age=0" in cleared.lower()
    assert cookie_attrs(cleared) == cookie_attrs(set_header)  # same Path / HttpOnly / SameSite (/ Secure)
    assert client.cookies.get("rx_session") is None           # the browser-side jar dropped it


def test_logout_clears_the_cookie_with_the_same_attributes(client):
    r = login(client)
    out = client.post("/api/auth/logout", headers={"X-CSRF-Token": r.json()["csrfToken"]})
    assert out.status_code == 204
    assert "max-age=0" in out.headers["set-cookie"].lower()
    assert cookie_attrs(out.headers["set-cookie"]) == cookie_attrs(r.headers["set-cookie"])
    assert client.cookies.get("rx_session") is None


def test_valid_session_check_leaves_the_cookie_alone(client):
    login(client)
    r = client.get("/api/auth/me")
    assert r.status_code == 200 and "set-cookie" not in r.headers


def test_no_cookie_means_401_without_any_set_cookie(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and "set-cookie" not in r.headers


# extra security checks
def test_state_changing_requests_need_an_allowed_origin(client):
    body = {"email": EMAIL, "password": PASSWORD, "remember": False}
    bad = client.post("/api/auth/login", json=body, headers={"Origin": "http://evil.example"})
    assert bad.status_code == 403
    del client.headers["Origin"]
    assert client.post("/api/auth/login", json=body).status_code == 403          # no Origin, no Referer
    ok = client.post("/api/auth/login", json=body, headers={"Referer": ORIGIN + "/login"})
    assert ok.status_code == 200                                                  # Referer fallback


def test_logging_in_again_replaces_the_old_session(client):
    login(client)
    first = client.cookies.get("rx_session")
    login(client)
    second = client.cookies.get("rx_session")
    assert first != second
    with TestClient(client.app, base_url="http://localhost:5173", cookies={"rx_session": first}) as old:
        assert old.get("/api/auth/me").status_code == 401


def test_repeated_failures_are_throttled_even_for_the_correct_password(client, settings):
    for _ in range(settings.login_max_failures):
        assert login(client, password=WRONG).status_code == 401
    blocked = login(client)                                  # correct password, but locked out
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0


def test_cors_preflight_allows_credentials_for_the_frontend_only(client):
    ok = client.options("/api/auth/login", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"})
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    assert ok.headers["access-control-allow-credentials"] == "true"
    bad = client.options("/api/auth/login", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_secure_cookie_flag_when_configured(settings, tmp_path):
    s = replace(settings, cookie_secure=True, database_path=str(tmp_path / "secure.db"))
    app = create_app(s)
    with connection(s.database_path) as conn:
        svc.create_user(conn, EMAIL, PASSWORD, "OWNER", time.time())
    with TestClient(app, base_url="https://localhost:5173") as c:
        c.headers["Origin"] = ORIGIN
        r = login(c)
    assert "secure" in r.headers["set-cookie"].lower()


def test_cleared_cookie_keeps_the_secure_flag_when_configured(settings, tmp_path):
    s = replace(settings, cookie_secure=True, database_path=str(tmp_path / "secure2.db"))
    app = create_app(s)
    with connection(s.database_path) as conn:
        svc.create_user(conn, EMAIL, PASSWORD, "OWNER", time.time())
    with TestClient(app, base_url="https://localhost:5173") as c:
        c.headers["Origin"] = ORIGIN
        r = login(c)
        out = c.post("/api/auth/logout", headers={"X-CSRF-Token": r.json()["csrfToken"]})
    assert out.status_code == 204
    assert "secure" in cookie_attrs(out.headers["set-cookie"])
    assert cookie_attrs(out.headers["set-cookie"]) == cookie_attrs(r.headers["set-cookie"])
