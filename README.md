# Business Forensics Platform

Phase 2 secure source ingestion for the Business Forensics Platform MVP.

Current gate status: Phase 2 revision is ready for gate review; Product Owner locked the 20 MB MVP default upload limit and deferred 100 MB/progress to Phase 7 or post-MVP.

## Stack

- Python 3.12
- FastAPI, Pydantic v2, SQLAlchemy 2, Alembic
- PostgreSQL 16
- Redis and Dramatiq worker shell
- React, TypeScript strict, Vite
- pytest and Playwright
- Docker Compose

## Local Python Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.lock
```

Run API with SQLite for quick local development:

```powershell
$env:APP_ENV = "development"
$env:AUTO_CREATE_DB = "true"
$env:DATABASE_URL = "sqlite:///./test-tmp/app.db"
$env:DEV_SEED_EMAIL = "admin@example.com"
$env:DEV_SEED_PASSWORD = "<set a local password>"
$env:ARTIFACT_STORAGE_ROOT = "./runtime-artifacts"
.\.venv\Scripts\python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000
```

## Local Web Setup

```powershell
npm install
npm run web:dev
```

The web app runs at `http://127.0.0.1:5173`.

## Docker Compose

Set a local seed password before starting the stack:

```powershell
$env:DEV_SEED_PASSWORD = "<set a local password>"
docker compose up --build
```

API health:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

## Tests

Python unit and integration tests:

```powershell
.\.venv\Scripts\python -m pytest
```

Frontend type/build check:

```powershell
npm run web:build
```

Playwright E2E:

```powershell
npm run test:e2e
```

The suite covers the Phase 1 mandatory flow and the Phase 2 upload -> inventory -> escaped source viewer flow.

The default MVP upload limit is `20 MB`. `MAX_UPLOAD_BYTES` is environment-configurable; 100 MB upload support and progress UI are formally deferred to Phase 7 or post-MVP.

## Implemented Scope

Foundation behavior:

- Opaque server-side sessions in HTTP-only cookies.
- CSRF protection for state-changing requests.
- Development seed user only under `APP_ENV=development`.
- Generic login errors and login rate limiting.
- Backend RBAC roles: `admin`, `analyst`, `reviewer`, `viewer`.
- Project create/list/get/update/archive.
- Project `PATCH` does not accept arbitrary `status`.
- Archive is irreversible and archived projects are read-only.
- Audit events for login/logout and project create/update/archive.
- API and worker health endpoints.

Secure ingestion behavior:

- Text and ZIP source upload.
- Immutable artifact storage under generated paths.
- Artifact inventory with SHA-256, encoding, line count, size, analysis status, and candidate count.
- ZIP traversal, symlink, nested archive, entry count, path length, decompression ratio, and total uncompressed size protections.
- Binary-looking and unsupported file warnings.
- Source viewer with line numbers and escaped untrusted source content.
- Project state and audit events for upload/ingestion success and failure.

Physical project deletion, extraction, evidence persistence, review workflow, AI adapter, behavioral tests, and export remain later phases.
