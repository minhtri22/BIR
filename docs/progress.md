# Project Progress

Date: 2026-08-06
Current phase: Phase 1 - Foundation
Status: PASS

## Phase 0

Closed status:

- `PHASE 0 - CLOSED_PASS`
- Baseline commit: `da2b7dc docs: complete phase 0 audit and planning`
- Revision commit: `e5ce32a docs: complete phase 0 planning and architecture baseline`
- Working tree was clean before Phase 1 started.

## Phase 1 Summary

Implemented:

- Modular monolith project scaffold under `apps/`, `packages/`, `migrations/`, and `tests/`.
- Python 3.12 FastAPI backend with Pydantic v2, SQLAlchemy 2, Alembic, and pytest.
- React + TypeScript strict + Vite frontend.
- PostgreSQL 16 + Redis + API + worker + web Docker Compose stack.
- Dramatiq/Redis worker shell.
- Opaque server-side session IDs in HTTP-only cookies.
- Pre-login CSRF nonce and session CSRF token validation for state-changing requests.
- Server-side session invalidation on logout.
- Idle and absolute session timeout enforcement.
- Development seed user only when `APP_ENV=development`; seed password comes from environment.
- Generic login failure response.
- Login rate limit by IP and account identifier hash.
- Backend RBAC roles: `admin`, `analyst`, `reviewer`, `viewer`.
- Project create/list/get/update/archive API.
- Project `PATCH` metadata updates only; arbitrary `status` mutation is rejected.
- Archive is irreversible in MVP; archived projects are read-only.
- Audit events for login/logout and project create/update/archive.
- Health endpoints for API and worker shell readiness.
- Minimal frontend login/project create/list UI.
- Mandatory Playwright E2E: login -> create project -> project appears in list.
- ADR-003 for project state machine as a business contract.
- README and CI workflow.

No Phase 2 source upload, extraction, review workflow implementation, AI adapter, behavioral tests, or export implementation was added.

## Commands Run

Setup and dependency installation:

- `py -3.12 -m venv .venv`
- `py -3.12 -m pip --python .venv install -r requirements.lock`
- `npm install`
- `npx playwright install chromium`

Verification:

- `.\.venv\Scripts\python -m pytest`
- `npm run web:build`
- `npm run test:e2e`
- `$env:DATABASE_URL='sqlite:///./runtime-tests/alembic.db'; .\.venv\Scripts\python -m alembic upgrade head`
- `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose config`
- `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose up -d db redis`
- `$env:DATABASE_URL='postgresql+psycopg://bfp:bfp_dev_password@127.0.0.1:55432/bfp'; .\.venv\Scripts\python -m alembic upgrade head`
- `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose up -d --build api worker web`
- `$env:DEV_SEED_PASSWORD='<local-dev-seed-password>'; docker compose ps`
- `Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health' | ConvertTo-Json -Compress`
- `Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing | Select-Object -ExpandProperty StatusCode`
- `npm audit --omit=dev`

## Test Result

Detailed test evidence is recorded in `docs/phase1_test_report.md`.

Summary:

- Python unit/integration tests: `17 passed`
- Frontend TypeScript/Vite build: passed
- Mandatory Playwright E2E: `1 passed`
- Alembic SQLite migration: passed
- Alembic PostgreSQL migration through Compose: passed
- Docker Compose full stack build/start: passed
- API health from Compose stack: `{"status":"ok","database":"ok","worker":null}`
- Web root from Compose stack: HTTP `200`
- Production npm dependency audit: `found 0 vulnerabilities`

## Requirements Covered

Phase 1 implemented or partially implemented:

- REQ-001 local login.
- REQ-002 roles and backend RBAC.
- REQ-003 project creation.
- REQ-004 project list/detail/update/archive.
- REQ-005 deterministic project state restrictions for Phase 1 actions.
- REQ-032 project-scoped foundation boundaries.
- REQ-035 Phase 1 auth/session/CSRF/RBAC/CORS/password/rate-limit subset.
- REQ-036 health endpoint and request ID foundation.
- REQ-038 Docker Compose and PostgreSQL migration.
- REQ-039 README and local commands.
- REQ-040 first two vertical-slice steps: login -> create project.

## Known Limitations

- Redis host port is `6380` to avoid an existing local port `6379` collision; API/worker still use internal Compose host `redis:6379`.
- PostgreSQL host port is `55432` to avoid an existing local port `5432` collision; Compose services still use `db:5432`.
- Full review workflow endpoint is only an RBAC-protected Phase 1 stub; implementation starts in Phase 4.
- Source upload, extraction, evidence persistence, AI adapter, behavioral tests, dashboard, and export remain later phases.
- `npm install` reports development-tool advisories, but `npm audit --omit=dev` reports zero production vulnerabilities.

## Open Assumptions

Open assumptions remain in `docs/assumptions.md`.

Phase 2 blocking assumptions: exact ZIP scanner numeric limits and content sniffing policy need to be locked before secure ingestion implementation.

## Next Phase

Phase 2 - Secure ingestion:

- Upload text files and ZIP packages.
- Safe ZIP extraction.
- Immutable source artifact inventory.
- Source viewer with escaping and line numbers.
- Ingestion audit events.
