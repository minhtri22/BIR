# Phase 2 Test Report

Date: 2026-08-06
Phase: Phase 2 - Secure Source Ingestion
Status: CONDITIONAL - revision complete, Product Owner decision required

## Scope Verified

Implemented and tested:

- Text source upload and ZIP upload.
- Immutable artifact storage with generated storage paths independent of user filenames.
- Source artifact metadata: SHA-256, encoding, line count, size, extension, analysis status, candidate count.
- Source inventory API and React inventory UI.
- Source viewer API and React viewer with line numbers and escaped untrusted source content.
- ZIP path traversal blocking.
- ZIP symlink blocking.
- Nested archive blocking.
- ZIP entry count, path length, decompression ratio, and total uncompressed size limits.
- Binary-looking and unsupported files return ingestion warnings and are not stored as source artifacts.
- Project state transition to `ingesting`, then `ready_for_analysis` on successful ingestion.
- Project state restoration to the previous stable state on failed/rejected ingestion.
- Audit events for upload accepted, ingestion completed, and ingestion failed/cancelled.
- Ingestion path does not execute uploaded source content.
- Bounded chunk reads stop when `MAX_UPLOAD_BYTES` is exceeded.
- Oversized upload rejection creates no artifact, restores project status, and writes failure audit.
- Filesystem/persistence failure handling cleans partial files and writes best-effort failure audit in a new transaction when the database is available.
- Source viewer verifies artifact SHA-256 before decoding and audits tampering.
- Legacy Japanese encodings `cp932` and `shift_jis` are checked before Western fallback encodings.
- Latin-1 fallback creates an `encoding_low_confidence` warning.
- Architectural security test checks ingestion code does not import/call dynamic execution paths.
- Docker Compose artifact volume for local immutable artifact storage.

## Commands Run

Dependency/runtime:

- `.\.venv\Scripts\python.exe -m ensurepip --upgrade`
- `.\.venv\Scripts\python.exe -m pip install -r requirements.lock`

Backend verification:

- `.\.venv\Scripts\python.exe -m pytest tests\unit tests\integration`
- `.\.venv\Scripts\python.exe -m pytest`

Frontend and browser verification:

- `npm run web:build`
- `npm run test:e2e`

Migration and Compose verification:

- `$env:DATABASE_URL = "sqlite:///runtime-tests/alembic-phase2-<guid>.db"; .\.venv\Scripts\alembic.exe upgrade head`
- `$env:DEV_SEED_PASSWORD = "<generated-one-off>"; docker compose up -d --build api worker web`
- `$env:DEV_SEED_PASSWORD = "<generated-one-off>"; docker compose exec -T api alembic current`
- `Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/health | ConvertTo-Json -Compress`
- `(Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing).StatusCode`
- `npm audit --omit=dev`

## Results

- Python unit/integration tests: `30 passed`
- Frontend TypeScript/Vite production build: passed
- Playwright E2E: `2 passed`
  - Phase 1 mandatory flow: login -> create project -> project appears in list.
  - Phase 2 flow: upload source -> inventory -> escaped source viewer.
- Alembic SQLite migration: upgraded through `0002_phase2_source_ingestion`.
- Alembic PostgreSQL migration in Compose API container: `0002_phase2_source_ingestion (head)`.
- Docker Compose full-stack rebuild/start: passed.
- API health: `{"status":"ok","database":"ok","worker":null}`
- Web root: HTTP `200`
- Production npm dependency audit: `found 0 vulnerabilities`

## Mandatory Test Mapping

- `TC-01`: covered by `test_tc01_zip_path_traversal_is_blocked_without_artifacts`.
- `TC-11` Phase 2 artifact portion: covered by `test_tc01_text_upload_persists_immutable_inventory_and_escaped_viewer`.
- `TC-15` ingestion portion: covered by `test_unsupported_and_binary_entries_return_warnings_without_execution` and `test_ingestion_module_has_no_dynamic_execution_paths`.

Additional Phase 2 security coverage:

- ZIP symlink, nested archive, decompression ratio: `test_tc11_zip_symlink_nested_archive_and_decompression_limits_are_blocked`.
- ZIP entry count, path length, total uncompressed size: `test_tc11_entry_count_path_length_and_uncompressed_limits_are_enforced`.
- Source viewer escaping: backend integration test plus Playwright source viewer test.
- Storage isolation: backend integration test asserts stored file is under the artifact root and storage path does not contain the original filename.
- Oversized upload: `test_oversized_upload_is_rejected_with_restore_and_failure_audit`.
- Bounded read stop behavior: `test_bounded_upload_reader_stops_after_limit_without_consuming_remaining_chunks`.
- Filesystem failure audit/cleanup: `test_filesystem_failure_cleans_partial_artifact_restores_status_and_audits`.
- Tampered artifact integrity: `test_tampered_artifact_is_rejected_and_audited`.
- Legacy Japanese encoding: `test_cp932_source_upload_records_legacy_japanese_encoding`.
- Latin-1 low-confidence fallback: `test_latin1_fallback_creates_low_confidence_encoding_warning`.

## Limitations

- Evidence records do not exist until later phases, so `TC-11` evidence/export usage remains deferred to Phase 4/7.
- SRS `Upload 100 MB có progress` is not closed. Product Owner must choose either:
  - Option A: implement 100 MB upload support plus progress in Phase 2.
  - Option B: keep MVP default upload limit at 20 MB and formally defer 100 MB/progress to Phase 7 or post-MVP.
- Artifact retention/cleanup policy remains a Phase 7 or post-MVP decision.
