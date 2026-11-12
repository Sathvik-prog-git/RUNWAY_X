# RUNWAY X backend (authentication)

FastAPI + SQLite (local) + Argon2. Endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, `GET /api/health`.

## First-time setup (Windows PowerShell)

```powershell
cd C:\RUNWAY_X\TEMP_CHECK\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements-dev.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `backend\.env` and paste the generated text after `SECRET_KEY=`. Never commit `.env`.

## Run the tests

```powershell
python -m pytest
```

## Create the first administrator

```powershell
python create_admin.py --email you@example.com
```

You type the password at a hidden prompt (min. 12 characters). It is stored only as an Argon2 hash.

## Start the backend, then the frontend

```powershell
uvicorn main:app --reload --port 8000
```
```powershell
cd C:\RUNWAY_X\TEMP_CHECK\frontend
npm.cmd run dev
```

Open http://localhost:5173 (the port is fixed; the backend only accepts requests from that origin).

## How it works

- Login creates a random 256-bit session token. The browser gets it in an **HttpOnly** cookie; the database stores only its **SHA-256 hash**.
- Normal login: ends after 12 h, or 2 h of inactivity. "Remember me": 30 days, or 7 days of inactivity.
- Logout revokes the session in the database. Changing identity (logging in again) revokes the previous session.
- CSRF: state-changing requests must come from an allowed `Origin`, cookies are `SameSite=Lax`, and logout also needs the per-session `X-CSRF-Token`.
- Login errors are identical for unknown email / wrong password / disabled account, and a password hash is checked every time (no timing hint).
- 5 failed attempts per email+IP in 15 minutes locks that pair out for the rest of the window (in memory; resets when the server restarts).

## Calling the API manually (curl needs an Origin header)

```powershell
curl.exe -i -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -H "Origin: http://localhost:5173" -d "{\"email\":\"you@example.com\",\"password\":\"...\"}"
```
