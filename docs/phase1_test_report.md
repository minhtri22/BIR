# Phase 1 Test Report

Date: 2026-08-06
Phase: 1 - Foundation
Status: PASS

## Scope

Phase 1 verification covers the runnable foundation:

- FastAPI backend scaffold.
- Opaque server-side session auth.
- HTTP-only session cookie.
- CSRF protection.
- Session invalidation and timeout behavior.
- Development seed user gating.
- Login rate limiting.
- Backend RBAC.
- Project create/list/get/update/archive.
- Project status mutation restrictions.
- Audit foundation.
- Alembic migration.
- Docker Compose stack.
- React/TypeScript/Vite frontend.
- Mandatory Playwright E2E login -> create project -> project appears in list.

Source upload, static extraction, evidence persistence, review workflow implementation, AI adapter, behavioral tests, dashboard, and export are outside Phase 1.

## Results

| Gate | Command | Result |
|---|---|---|
| Python unit/integration tests | `.\.venv\Scripts\python -m pytest` | Passed: `17 passed in 6.10s` |
| Frontend type/build | `npm run web:build` | Passed |
| Mandatory E2E | `npm run test:e2e` | Passed: `1 passed` |
| Alembic SQLite migration | `$env:DATABASE_URL='sqlite:///./runtime-tests/alembic.db'; .\.venv\Scripts\python -m alembic upgrade head` | Passed |
| Compose config | `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose config` | Passed |
| Compose PostgreSQL/Redis | `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose up -d db redis` | Passed |
| Alembic PostgreSQL migration | `$env:DATABASE_URL='postgresql+psycopg://bfp:bfp_dev_password@127.0.0.1:55432/bfp'; .\.venv\Scripts\python -m alembic upgrade head` | Passed |
| Full Compose stack | `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose up -d --build api worker web` | Passed |
| API health | `Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health'` | Passed: `{"status":"ok","database":"ok","worker":null}` |
| Web root | `Invoke-WebRequest -Uri 'http://127.0.0.1:5173'` | Passed: HTTP `200` |
| Production dependency audit | `npm audit --omit=dev` | Passed: `found 0 vulnerabilities` |

## Python Test Coverage

The Python suite verifies:

- Health endpoint.
- Generic login failure message for unknown account and wrong password.
- Pre-auth CSRF required for login.
- Production session cookie flags include `HttpOnly`, `SameSite=Lax`, and `Secure`.
- Project create rejects missing session CSRF.
- Project create/list/update/archive happy path.
- Project creation starts in `draft`.
- `PATCH /projects/{id}` rejects arbitrary `status`.
- Archived projects are read-only.
- Project create/update/archive audit events are emitted.
- Viewer cannot create projects.
- Viewer cannot call the review endpoint.
- Logout invalidates server-side session.
- Idle-expired sessions are rejected.
- Development seed user requires an environment password.
- Development seed user can log in when configured.
- Login rate limit is keyed by account identifier and IP.
- Project state domain rules reject invalid transitions.

## Mandatory E2E Evidence

Playwright test:

```text
login -> create project -> project appears in list
```

Result:

```text
1 passed
```

This satisfies the Phase 1 gate that Phase 1 cannot be marked `PASS` without the E2E passing.

## Infrastructure Notes

- PostgreSQL uses `postgres:16-alpine`, satisfying the PostgreSQL 16 requirement.
- PostgreSQL host port is `55432` because host port `5432` was already occupied locally.
- Redis host port is `6380` because host port `6379` was already occupied locally.
- Compose service-to-service connections still use `db:5432` and `redis:6379`.
- `DEV_SEED_PASSWORD` is required by Compose config and was supplied only as a local verification environment variable.

## Result

Phase 1 is `PASS`.
