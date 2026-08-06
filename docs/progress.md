# Project Progress

Date: 2026-08-06
Current phase: Phase 3 - Static Extraction Design
Status: Phase 3 implementation contract revised; implementation blocked pending Architect `CLOSED_PASS_DESIGN`

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

Closed status:

- `PHASE 1 - CLOSED_PASS`
- Foundation commit after seed-password hygiene amend: `e4cdaab feat: complete phase 1 foundation`

## Phase 2 Summary

Implemented:

- Source upload endpoint for text files and ZIP packages.
- `SourceArtifact` and `IngestionWarning` persistence with Alembic migration `0002_phase2_source_ingestion`.
- Immutable artifact file writes under generated storage paths that do not use user filenames.
- SHA-256, encoding, line count, size, extension, analysis status, and candidate count inventory metadata.
- Safe ZIP validation before storage write:
  - path traversal blocked;
  - symlink entries blocked;
  - nested archives blocked;
  - entry count, path length, decompression ratio, and total uncompressed size limits enforced;
  - Unicode path normalization;
  - duplicate normalized paths blocked.
- Extension allowlist for `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`.
- Binary-looking and unsupported entries return warnings and are not stored as source artifacts.
- Source inventory API and UI.
- Source viewer API and UI with line numbers and escaped untrusted source content.
- Project lifecycle integration:
  - upload acceptance moves eligible projects to `ingesting`;
  - successful ingestion moves to `ready_for_analysis`;
  - failed/rejected ingestion restores the previous stable state.
- Audit events for `SOURCE_UPLOAD_ACCEPTED`, `INGESTION_COMPLETED`, and `INGESTION_FAILED_OR_CANCELLED`.
- Compose artifact storage volume at `/app/runtime-artifacts`.
- Phase 2 Playwright E2E for upload -> inventory -> escaped source viewer.
- Revision: bounded chunk upload reads stop when `MAX_UPLOAD_BYTES` is exceeded.
- Revision: oversized upload restores project status, creates no artifact, and writes failure audit.
- Revision: filesystem/persistence failures clean partially written files and write best-effort failure audit in a new transaction when the database is available.
- Revision: source viewer verifies stored artifact SHA-256 before decoding and audits integrity mismatch.
- Revision: legacy Japanese encodings `cp932` and `shift_jis` are checked before Western fallback encodings.
- Revision: Latin-1 fallback creates an `encoding_low_confidence` warning.
- Revision: architectural security test checks ingestion does not import/call dynamic execution paths.

No Phase 3 extraction, candidate generation, evidence model, review workflow, AI adapter, behavioral tests, or export implementation was added.

Phase 2 gate and merge:

- Architect gate review: APPROVED.
- PR #1 merged into `main`.
- Merge commit: `ead94f7a15956b7185a4fa66f8e83cb973a22be1`.

## Phase 3 Design Summary

Created design-only contract:

- `docs/implementation_contract/phase3_static_extraction_contract.md`

The contract defines:

- Phase objective and out-of-scope boundaries.
- Requirement traceability for REQ-011, REQ-012, REQ-013, REQ-017, REQ-018, REQ-019, REQ-033, REQ-035, REQ-036, and REQ-040.
- Domain model and schema contract for `SourceChunk`, `AnalyzerVersion`, `AnalysisJob`, candidate `BusinessStatement`, `Evidence`, `AnalysisGap`, and `UnresolvedQuestion`.
- Project, artifact, and job state model for static analysis.
- Chunking, deterministic static extractor patterns, candidate rules, evidence rules, idempotency, API, UI, security, transaction/failure, migration, test matrix, and DoD.

Revision required by design review has been applied in documentation:

- Retry/idempotency now uses `request_fingerprint` shared across retries plus per-attempt `attempt_no`.
- MVP now allows only one active analysis job per project.
- Client no longer submits analyzer identity; server owns analyzer name, version, pattern set hash, supported configuration, and canonical config hash.
- Analysis failure/cancel transition is locked as `analyzing -> previous_project_status`, defaulting to `ready_for_analysis`, with audit `ANALYSIS_FAILED_OR_CANCELLED`.
- Evidence target integrity requires a DB exactly-one-target check.
- Candidate, evidence, gap, and question provenance includes `analysis_job_id` and `created_by_kind`.
- `source_artifacts.candidate_count` remains a transactionally maintained cache; `business_statements.evidence_count` is not persisted in Phase 3.
- Candidate identity is provenance-based and does not primarily depend on natural-language statement text.

No Phase 3 implementation code, migration, API, worker, or UI was added.

## Commands Run

Phase 3 design revision:

- `rg` checks for stale blocker wording and idempotency/API contradictions.
- `git diff --check`

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
- `.\.venv\Scripts\python.exe -m ensurepip --upgrade`
- `.\.venv\Scripts\python.exe -m pip install -r requirements.lock`
- `.\.venv\Scripts\python.exe -m pytest tests\unit tests\integration`
- `$env:DATABASE_URL='sqlite:///runtime-tests/alembic-phase2-<guid>.db'; .\.venv\Scripts\alembic.exe upgrade head`
- `$env:DEV_SEED_PASSWORD='<generated-one-off>'; docker compose up -d --build api worker web`
- `$env:DEV_SEED_PASSWORD='<generated-one-off>'; docker compose exec -T api alembic current`

## Test Result

Detailed test evidence is recorded in `docs/phase1_test_report.md` and `docs/phase2_test_report.md`.

Summary:

- Python unit/integration tests: `30 passed`
- Frontend TypeScript/Vite build: passed
- Playwright E2E: `2 passed`
- Alembic SQLite migration: passed through `0002_phase2_source_ingestion`
- Alembic PostgreSQL migration through Compose: `0002_phase2_source_ingestion (head)`
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

Phase 2 implemented or partially implemented:

- REQ-006 source upload for text and ZIP with no source execution.
- REQ-007 supported extension allowlist and unsupported/binary warnings.
- REQ-008 safe ZIP validation and storage isolation.
- REQ-009 immutable artifact inventory metadata.
- REQ-010 source viewer line numbers and escaping; evidence highlighting remains later.
- REQ-035 ingestion/source-viewer security subset.
- REQ-037 upload-size enforcement subset; MVP default is 20 MB, the limit remains environment-configurable, and 100 MB + progress is formally deferred to Phase 7 or post-MVP.
- REQ-040 third vertical-slice step: upload one source file.

Phase 3 design covered, not implemented:

- REQ-011 static extraction contract.
- REQ-012 deterministic pattern contract.
- REQ-013 async/idempotent analysis job contract, revised for request fingerprint, attempts, retry lineage, and one active job per project.
- REQ-017 candidate schema and queue contract.
- REQ-018 evidence-required candidate rule plus gap/question fallback contract, including DB exactly-one-target evidence constraint.
- REQ-019 evidence schema continuation contract with `analysis_job_id` provenance.
- REQ-033 uncertainty object contract.

## Known Limitations

- Redis host port is `6380` to avoid an existing local port `6379` collision; API/worker still use internal Compose host `redis:6379`.
- PostgreSQL host port is `55432` to avoid an existing local port `5432` collision; Compose services still use `db:5432`.
- Full review workflow endpoint is only an RBAC-protected Phase 1 stub; implementation starts in Phase 4.
- Extraction, evidence persistence, AI adapter, behavioral tests, dashboard, and export remain later phases.
- The default MVP upload limit is 20 MB. `MAX_UPLOAD_BYTES` remains environment-configurable; upload 100 MB plus progress UI is deferred to Phase 7 or post-MVP by Product Owner decision on 2026-08-06.
- Evidence/export usage of artifact hashes remains deferred until evidence and export models exist.
- `npm install` reports development-tool advisories, but `npm audit --omit=dev` reports zero production vulnerabilities.

## Open Assumptions

Open assumptions remain in `docs/assumptions.md`.

Phase 3 implementation blocking assumptions:

- Architect must review the design PR and return `CLOSED_PASS_DESIGN`.
- ADR-003 must be updated during implementation with the now-locked `fail_or_cancel_analysis` transition from `analyzing` to `previous_project_status`.

## Next Phase

Phase 3 implementation, blocked until Architect `CLOSED_PASS_DESIGN`:

- Source chunking and deterministic static extractor.
- Analyzer versioning and idempotency by artifact hash, server-owned analyzer/config, request fingerprint, and attempt number.
- Candidate, gap/question, and evidence persistence.
- Candidate queue UI.
