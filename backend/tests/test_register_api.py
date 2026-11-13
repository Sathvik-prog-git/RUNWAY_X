"""End-to-end tests of POST /api/auth/register through the real FastAPI app (needs fastapi + httpx + argon2)."""
import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import auth_service as svc  # noqa: E402
from conftest import EMAIL, ORIGIN, PASSWORD  # noqa: E402
from db import connection  # noqa: E402
from main import create_app  # noqa: E402

GOOD = {
    "full_name": "Asha Rao",
    "email": "Asha@Acme.in",
    "password": "a-long-unusual-passphrase",
    "confirm_password": "a-long-unusual-passphrase",
    "company_name": "Acme Castings",
    "phone": "98765 43210",
}


@pytest.fixture
def app(settings):
    app = create_app(settings)
    clock = {"now": time.time()}
    app.state.clock = lambda: clock["now"]
    with connection(settings.database_path) as conn:
        svc.create_user(conn, EMAIL, PASSWORD, "SUPER_ADMIN", clock["now"])
    return app


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost:5173") as c:
        c.headers["Origin"] = ORIGIN
        yield c


def register(client, **overrides):
    return client.post("/api/auth/register", json={**GOOD, **overrides})


def counts(settings):
    with connection(settings.database_path) as c:
        return (c.execute("SELECT COUNT(*) FROM companies").fetchone()[0], c.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def test_register_creates_owner_company_and_signs_in(client, settings):
    r = register(client, gstin="22aaaaa0000a1z5")
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "OWNER" and body["user"]["email"] == "asha@acme.in" and body["csrfToken"]
    assert "httponly" in r.headers["set-cookie"].lower() and r.headers["cache-control"] == "no-store"
    assert client.get("/api/auth/me").json()["user"]["role"] == "OWNER"      # the new session works
    with connection(settings.database_path) as c:
        u = c.execute("SELECT * FROM users WHERE email = 'asha@acme.in'").fetchone()
        co = c.execute("SELECT * FROM companies WHERE id = ?", (u["company_id"],)).fetchone()
    assert u["phone"] == "+919876543210" and co["gstin"] == "22AAAAA0000A1Z5" and "$argon2" in u["password_hash"]
    assert "a-long-unusual-passphrase" not in u["password_hash"]


@pytest.mark.parametrize("field,value", [
    ("role", "SUPER_ADMIN"), ("role", "OWNER"), ("company_id", 1), ("is_active", True), ("is_admin", True),
])
def test_clients_cannot_inject_role_company_or_privileges(client, settings, field, value):
    r = register(client, **{field: value})
    assert r.status_code == 422
    assert counts(settings) == (0, 1)               # nothing created; only the seeded SUPER_ADMIN exists


def test_duplicate_email_gets_generic_error_and_creates_no_company(client, settings):
    assert register(client).status_code == 201
    client.cookies.clear()
    dup = register(client, email="ASHA@acme.in", company_name="Another Co")
    assert dup.status_code == 409
    assert "email" not in dup.json()["detail"].lower() and "already exists" not in dup.json()["detail"].lower()
    assert "set-cookie" not in dup.headers
    seeded = register(client, email=EMAIL)           # the SUPER_ADMIN's email gives the identical response
    assert seeded.status_code == 409 and seeded.json() == dup.json()
    assert counts(settings) == (1, 2)


def test_gstin_must_be_unique_but_blank_may_repeat(client, settings):
    assert register(client, gstin="22AAAAA0000A1Z5").status_code == 201
    client.cookies.clear()
    r = register(client, email="b@acme.in", gstin="22AAAAA0000A1Z5")
    assert r.status_code == 409 and "GSTIN" in r.json()["detail"]
    assert counts(settings) == (1, 2)
    assert register(client, email="c@acme.in").status_code == 201
    client.cookies.clear()
    assert register(client, email="d@acme.in", gstin="").status_code == 201


@pytest.mark.parametrize("override", [
    {"confirm_password": "something-else-entirely"},
    {"password": "short", "confirm_password": "short"},
    {"phone": "12345"},
    {"phone": "+44 7911 123456"},
    {"gstin": "NOT-A-GSTIN"},
    {"email": "not-an-email"},
    {"full_name": " "},
    {"company_name": ""},
])
def test_invalid_input_is_rejected(client, settings, override):
    assert register(client, **override).status_code == 422
    assert counts(settings) == (0, 1)


def test_registered_owner_can_log_out_and_log_in_again(client):
    csrf = register(client).json()["csrfToken"]
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    r = client.post("/api/auth/login", json={"email": "asha@acme.in", "password": GOOD["password"], "remember": False})
    assert r.status_code == 200 and r.json()["user"]["role"] == "OWNER"


def test_origin_guard_still_applies(client, settings):
    client.headers.pop("Origin")
    assert register(client).status_code == 403
    client.headers["Origin"] = "http://evil.example"
    assert register(client).status_code == 403
    assert counts(settings) == (0, 1)


def test_registration_is_rate_limited_per_ip(client):
    for i in range(20):
        assert register(client, email=f"user{i}@acme.in", phone="9876543210").status_code in (201, 409)
        client.cookies.clear()
    r = register(client, email="late@acme.in")
    assert r.status_code == 429 and "retry-after" in r.headers
