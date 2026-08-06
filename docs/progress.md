# Project Progress

Date: 2026-08-06
Current phase: Phase 4 - Epic 4.1 Review Domain Design
Status: Epic 4.1 design revision drafted after Architect `REVISION_REQUIRED`; implementation not started

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

Phase 3 design gate:

- Architect verdict: `CLOSED_PASS_DESIGN`.
- Implementation authorized on branch `phase-3-static-extraction`.

## Phase 3 Implementation Summary

Implemented:

- Alembic migration `0003_phase3_static_extraction`.
- SQLAlchemy models for `AnalyzerVersion`, `AnalysisJob`, `AnalysisJobArtifact`, `SourceChunk`, `BusinessStatement`, `Evidence`, `AnalysisGap`, and `UnresolvedQuestion`.
- Deterministic chunking with source line ranges and chunk hashes.
- Server-owned analyzer identity: `static-cobol-mvp` version `0.1.0`.
- Canonical allowlisted configuration and configuration hashing.
- Static extraction patterns for IF/ELSE, EVALUATE/WHEN, assignment, SQL, procedure/program calls, status literals, numeric thresholds, date logic, role/user checks, and comment-adjacent logic.
- Analysis job API:
  - create job;
  - retry failed/cancelled job;
  - list/get jobs;
  - list/get candidate statements;
  - list statement evidence;
  - list analysis gaps and unresolved questions.
- Idempotency and retry:
  - `request_fingerprint` reused across retry attempts;
  - per-attempt `attempt_no`;
  - succeeded request fingerprint returns the existing job;
  - active project job returns HTTP `409`;
  - failed/cancelled job can create the next attempt.
- MVP concurrency guard: one active analysis job per project.
- Project state transitions:
  - `ready_for_analysis -> analyzing -> review_in_progress`;
  - failure restores `AnalysisJob.previous_project_status`.
- Audit events for `ANALYSIS_STARTED`, `ANALYSIS_COMPLETED`, and `ANALYSIS_FAILED_OR_CANCELLED`.
- Evidence exactly-one-target DB check constraint.
- Candidate/evidence/gap/question provenance through `analysis_job_id`.
- Insert-only static extractor invariant:
  - no candidate update;
  - no candidate upsert;
  - no candidate merge;
  - no lineage mutation before Phase 4.
- Candidate queue UI with job status, candidate list, evidence list, and highlighted source line navigation.
- Dramatiq actor shell entrypoint for static analysis job processing, sharing the API analysis service.
- Phase 3 Playwright E2E for upload -> run analysis -> candidate -> evidence source highlight.

No Phase 4 review workflow, AI adapter, behavioral tests, dashboard, or export implementation was added.

Phase 3 implementation gate:

- Architect verdict: `CLOSED_PASS`.
- Architect review confirmed scope discipline, migration quality, idempotency, active-job enforcement, server-owned analyzer identity, insert-only candidate invariant, evidence provenance, candidate queue UI, and test coverage.
- Phase 3 remains the baseline for Phase 4 review workflow work.

## Phase 4 Epic 4.1 Review Domain Design Summary

Created design-only contract:

- `docs/implementation_contract/epic4_1_review_domain_contract.md`

The contract defines:

- Review Domain as human validation, not approval workflow.
- Out-of-scope boundaries for AI, workflow engine, BPM, DMN, rule engine, merge, export, glossary, behavioral tests, and runtime.
- Domain model for `ReviewDecision`, `ReviewRecord`, `ReviewSession`, `ReviewReason`, `ReviewContext`, `ReviewEvidenceSnapshot`, `ReviewOutcome`, `ReviewAttachment`, `ReviewFlag`, and `ReviewConflictMarker`.
- `ReviewDecision` values for `VERIFY`, `REJECT`, `NEEDS_MORE_EVIDENCE`, `DUPLICATE`, `OUT_OF_SCOPE`, and `UNABLE_TO_DECIDE`.
- `OBSOLETE` excluded from ReviewDecision because obsolete lifecycle handling belongs to Epic 4.4 Revision Lineage.
- One active `ReviewSession` per `BusinessStatement`.
- Required `analysis_job_id` provenance on ReviewEvidenceSnapshot.
- Structured ReviewReason as `reason_code` plus `reason_detail`.
- `ReviewOutcome` as derived from BusinessStatement state plus latest immutable ReviewRecord, not persisted.
- Invariant that ReviewRecord never references another ReviewRecord.
- Immutable ReviewRecord, ReviewDecision, and ReviewEvidenceSnapshot semantics.
- `verified` as a contextual review fact, not ground truth.
- API and UI contracts for review sessions, review decisions, review queue, pending/verified/rejected lists, evidence viewer, decision panel, and history.
- Atomic transaction semantics for review decision, review record, evidence snapshot, audit, and derived statement status outcome.
- Test matrix for unit, integration, migration, RBAC, immutable review, state transition, evidence snapshot, audit, E2E, and no-execution architectural checks.

No Phase 4 implementation code, migration, API route, UI component, AI adapter, merge logic, behavioral test, dashboard, or export implementation was added.

Epic 4.1 design gate:

- Status: `DESIGN_REVISION_DRAFT`.
- Awaiting Architect Review.

## Commands Run

Phase 3 implementation:

- `pytest`
- `npm run web:build`
- `npm run test:e2e`
- `$env:DATABASE_URL='sqlite:///./test-tmp/phase3-migration.sqlite'; .\.venv\Scripts\python.exe -m alembic upgrade head`
- `$env:DEV_SEED_PASSWORD='<local-temporary>'; docker compose up -d --build`
- `$env:DATABASE_URL='postgresql+psycopg://bfp:bfp_dev_password@127.0.0.1:55432/bfp'; .\.venv\Scripts\python.exe -m alembic upgrade head`
- `$env:DATABASE_URL='postgresql+psycopg://bfp:bfp_dev_password@127.0.0.1:55432/bfp'; .\.venv\Scripts\python.exe -m alembic current`
- `Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/health`
- `Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing`
- `npm audit --omit=dev`

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

Detailed test evidence is recorded in `docs/phase1_test_report.md`, `docs/phase2_test_report.md`, and `docs/phase3_test_report.md`.

Summary:

- Python unit/integration tests: `43 passed`
- Frontend TypeScript/Vite build: passed
- Playwright E2E: `3 passed`
- Alembic SQLite migration: passed through `0003_phase3_static_extraction`
- Alembic PostgreSQL migration through Compose: `0003_phase3_static_extraction (head)`
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

Phase 3 implemented:

- REQ-011 static extraction.
- REQ-012 deterministic patterns.
- REQ-013 async/idempotent analysis jobs.
- REQ-017 candidate schema and queue.
- REQ-018 evidence-required candidate rule plus gap/question fallback.
- REQ-019 Phase 3 evidence schema and evidence navigation.
- REQ-033 uncertainty objects through `AnalysisGap` and `UnresolvedQuestion`.
- REQ-040 vertical slice through candidate/evidence.

## Known Limitations

- Redis host port is `6380` to avoid an existing local port `6379` collision; API/worker still use internal Compose host `redis:6379`.
- PostgreSQL host port is `55432` to avoid an existing local port `5432` collision; Compose services still use `db:5432`.
- Full review workflow endpoint is only an RBAC-protected Phase 1 stub; Epic 4.1 currently adds design only.
- Review workflow, AI adapter, behavioral tests, dashboard, and export remain later phases.
- The default MVP upload limit is 20 MB. `MAX_UPLOAD_BYTES` remains environment-configurable; upload 100 MB plus progress UI is deferred to Phase 7 or post-MVP by Product Owner decision on 2026-08-06.
- Export usage of artifact hashes remains deferred until export models exist.
- `npm install` reports development-tool advisories, but `npm audit --omit=dev` reports zero production vulnerabilities.

## Open Assumptions

Open assumptions remain in `docs/assumptions.md`.

Epic 4.1 design blocking assumptions:

- None for drafting the design contract.
- Implementation remains blocked until Architect Review approves the Epic 4.1 revised contract.

## Next Phase

Phase 4 Epic 4.1 Review Domain:

- Design drafted.
- Design revision drafted after Architect review.
- Implementation not started.
- Awaiting Architect Review.

Phase 4 review workflow, implementation not started:

- Human review decisions.
- Reviewer verification gate.
- Candidate revision/lineage.
- Review audit history.

Delivery model from Phase 4 onward:

- Work is split into Epics instead of one large phase implementation.
- Each Epic should have a small contract or scope note before implementation.
- Each Epic should be implemented, tested, documented, committed, and reviewed independently.
- Phase 4 can close only after all required Phase 4 Epics pass review.

Planned Phase 4 Epics:

- Epic 4.1 - Review Domain.
- Epic 4.2 - Review API.
- Epic 4.3 - Review UI.
- Epic 4.4 - Revision Lineage.
- Epic 4.5 - Review Audit.
