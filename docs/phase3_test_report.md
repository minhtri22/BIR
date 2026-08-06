# Phase 3 Static Extraction Test Report

Date: 2026-08-06
Status: CLOSED_PASS
Branch: `phase-3-static-extraction`

Architect verdict:

- Phase 3 implementation: `CLOSED_PASS`.
- Scope, migration, idempotency, active-job model, analyzer ownership, insert-only invariant, evidence provenance, UI, and tests accepted.

## Scope Verified

Phase 3 implementation covers:

- Alembic migration `0003_phase3_static_extraction`.
- Server-owned analyzer identity `static-cobol-mvp` version `0.1.0`.
- Deterministic chunking with line-range provenance.
- Static pattern extraction for IF/ELSE, EVALUATE/WHEN, assignment, SQL, procedure calls, status literals, numeric thresholds, date logic, role/user checks, and comment-adjacent logic.
- Insert-only candidate, evidence, gap, and unresolved-question persistence.
- `request_fingerprint` plus `attempt_no` retry/idempotency model.
- One active analysis job per project.
- Evidence exactly-one-target DB constraint.
- Candidate queue UI and source/evidence navigation.
- No source execution architectural test coverage.

## Verification Results

| Check | Command | Result |
|---|---|---|
| Python unit/integration tests | `pytest` | Passed: `43 passed` |
| Frontend production build | `npm run web:build` | Passed |
| Playwright E2E | `npm run test:e2e` | Passed: `3 passed` |
| SQLite Alembic migration | `$env:DATABASE_URL='sqlite:///./test-tmp/phase3-migration.sqlite'; .\.venv\Scripts\python.exe -m alembic upgrade head` | Passed through `0003_phase3_static_extraction` |
| PostgreSQL Compose migration | `$env:DATABASE_URL='postgresql+psycopg://bfp:bfp_dev_password@127.0.0.1:55432/bfp'; .\.venv\Scripts\python.exe -m alembic upgrade head` | Passed |
| PostgreSQL current revision | same env, `.\.venv\Scripts\python.exe -m alembic current` | `0003_phase3_static_extraction (head)` |
| Docker Compose build/start | `$env:DEV_SEED_PASSWORD='<local-temporary>'; docker compose up -d --build` | Passed |
| Docker Compose status | `$env:DEV_SEED_PASSWORD='<local-temporary>'; docker compose ps` | API, DB, Redis, web, worker up; DB/Redis healthy |
| API health | `Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/health` | `status=ok`, `database=ok` |
| Web HTTP | `Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing` | HTTP `200` |
| Production dependency audit | `npm audit --omit=dev` | `found 0 vulnerabilities` |

Notes:

- Initial sandboxed `npm run web:build` and `npm run test:e2e` hit `spawn EPERM`; both passed when rerun outside the sandbox.
- API executes analysis through FastAPI background tasks for the MVP vertical slice. A Dramatiq actor is also present and calls the same analysis service; the Compose worker shell remains running.
- The local Compose seed password was supplied only through process environment and was not written to tracked files.

## Test Coverage Highlights

Unit tests:

- Deterministic chunking and line-range preservation.
- Static pattern coverage for every contracted Phase 3 pattern.
- Unknown configuration and unsupported pattern rejection.
- Candidate identity does not depend on natural-language statement text.
- Project-state transitions for `start_analysis`, `complete_analysis`, and `fail_or_cancel_analysis`.
- Architectural no-execution scan across ingestion, analysis, extraction, router, and worker modules.

Integration tests:

- Analysis job creates candidates, evidence, gaps, unresolved questions, artifact candidate counts, and audit events.
- Succeeded request fingerprint reuses the existing job and does not duplicate candidates.
- New analysis run with a different config inserts new candidates without updating existing `BusinessStatement` rows.
- Active project job rejects new analysis requests with HTTP `409`.
- Unknown config is rejected and client-owned analyzer identity is rejected.
- Failed analysis restores project status and retry creates the next attempt.
- Evidence exactly-one-target database constraint is enforced.

E2E tests:

- Phase 1: login -> create project -> project appears in list.
- Phase 2: upload source -> inventory -> escaped source viewer.
- Phase 3: upload source -> run static analysis -> candidate appears -> evidence opens highlighted source line.

## Gate-Relevant Assertions

- Static extractor never updates or upserts existing candidates.
- Every candidate has evidence.
- If static extraction finds uncertainty without a verified business claim, it records `AnalysisGap` or `UnresolvedQuestion`.
- Source remains untrusted text and is not executed.
- Analyzer identity is owned by the server.
- Project transitions follow `ready_for_analysis -> analyzing -> review_in_progress`, with failure restoring `previous_project_status`.
- Phase 4 review workflow was not implemented.
