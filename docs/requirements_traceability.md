# Requirements Traceability Matrix

Date: 2026-08-06
Phase: 3 static extraction design
Status: Phase 3 implementation contract drafted; implementation blocked pending Architect `CLOSED_PASS_DESIGN`.

Sources:

- SRS: `docs/01_business_forensics_mvp_requirements.md`
- Business Analysis: `docs/02_business_forensics_mvp_business_analysis.md`
- Handoff: `docs/00_CODEX_HANDOFF_BUSINESS_FORENSICS_MVP.md`

Status legend:

- `Planned`: not implemented yet.
- `Partially implemented`: current phase implemented an explicitly scoped subset.
- `Implemented`: implemented and verified in code.
- `Blocked/Clarify`: cannot be completed until a decision is made.

## End-to-End Matrix

| Requirement ID | Source reference | Requirement | Business rule / constraint | Module / API / UI | Planned phase | Status | Acceptance evidence |
|---|---|---|---|---|---|---|---|
| REQ-001 | SRS Section 11 Authentication; SRS Section 15 Security; BA Risk 5; BA BR-013 | User can log in locally. | Password uses Argon2 or bcrypt; login errors are generic; session behavior follows ADR-002. | Auth, User, Audit; `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`; Login UI | Phase 1 | Implemented | `test_auth_projects.py`, Playwright E2E, cookie/session/CSRF/rate-limit tests |
| REQ-002 | SRS Section 5 Personas; SRS Section 15 Security; BA Sections 5 and 13; BA BR-013 | Roles exist for `admin`, `analyst`, `reviewer`, `viewer`. | Backend RBAC is authoritative; viewer cannot review. | Auth, RBAC, Domain policy; role-aware API dependencies and UI actions | Phase 1 | Implemented | RBAC integration tests; TC-10 viewer review forbidden |
| REQ-003 | SRS Section 7 UC-01; SRS Section 11 Projects; BA BP-01; BA BR-013 | Admin or analyst can create a project. | One project represents one legacy system scope and snapshot; create must audit `PROJECT_CREATED`; creation starts in `draft`. | Project Service, Audit; `POST /api/v1/projects`; Project create UI | Phase 1 | Implemented | Project create integration test, audit-on-create test, Playwright login -> create project -> list E2E |
| REQ-004 | SRS Section 7 UC-01; SRS Section 11 Projects; BA BP-01; BA BR-013 | Project list/detail/update/archive. | Important project changes create audit events; archive is irreversible in MVP; physical deletion is excluded. | Project Service, Project state, Audit; `GET/PATCH /api/v1/projects`, `POST /api/v1/projects/{id}/archive`; Project list/detail UI | Phase 1 | Implemented | Project CRUD/archive integration tests, audit tests, archive-readonly test |
| REQ-005 | SRS Section 8.1 Project; BA BP-01/BP-02/BP-09; BA BR-013 | Project status supports a deterministic draft-to-archive lifecycle. | Project status transitions follow ADR-003; `PATCH /projects/{id}` cannot set status arbitrarily. | Domain state machine, Project Service; Project API and dashboard status | Phase 1 | Implemented | State transition unit tests, API invalid-status PATCH test |
| REQ-006 | SRS Section 7 UC-02; SRS Section 15 Security; Handoff Security gates; BA BP-02; BA BR-006 | Upload text source files and ZIP packages. | Source is untrusted input; source upload is never executed. | Ingestion Service, Storage; `POST /api/v1/projects/{projectId}/artifacts/upload`; Upload UI | Phase 2 | Implemented | TC-01, TC-15 ingestion portion, upload integration tests, Phase 2 Playwright upload test |
| REQ-007 | SRS Section 7 UC-02; BA BP-02; BA BR-016 | Support extensions `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`. | Unsupported/binary files are not silently ignored; warnings are required. | Ingestion Service; Upload API response and inventory warnings | Phase 2 | Implemented | Binary/unsupported warning integration test |
| REQ-008 | SRS Section 7 UC-02; SRS Section 15 Security; Handoff Security gates; BA Risk 5; BA BR-006 | ZIP extraction must be safe. | Block path traversal, symlink, nested archive, path length, entry count, ratio, and ZIP bomb attacks; filename must not drive storage path. | Ingestion Security, Storage; Upload API | Phase 2 | Implemented | TC-01, decompression ratio regression, storage isolation regression, symlink/nested ZIP tests, entry/path/total-size limit tests |
| REQ-009 | SRS Section 7 UC-03; SRS Section 10.2 SourceArtifact; BA Capability 1; BA BR-006 | Artifact inventory records path, type, size, encoding, SHA-256, line count, analysis status, candidate count. | Original artifacts are immutable; evidence points to artifact hash. | SourceArtifact, Ingestion Service; inventory API and UI | Phase 2 | Implemented | TC-11 artifact portion, inventory integration test; evidence/export hash consumers remain Phase 4/7 |
| REQ-010 | SRS Section 7 UC-06; SRS Section 12.4 Source explorer; SRS Section 15 Security; BA Evidence model; BA BR-006 | Source content can be viewed with line numbers and evidence highlighting. | Source excerpt/content is HTML-escaped and treated as untrusted text. | Source Viewer, Evidence UI; artifact content API and source explorer UI | Phase 2 | Partially implemented | Source viewer API/UI, HTML escaping integration test, Phase 2 Playwright viewer test; evidence highlighting remains Phase 4 |
| REQ-011 | SRS Section 7 UC-04; SRS Section 14 Static extraction; BA BP-03; BA BR-002 | Static extraction creates deterministic candidates. | Static extractor only creates `candidate`; no auto-verify. | Extraction, Analysis Orchestrator, Statement Service; analysis job API and candidate queue UI | Phase 3 | Planned | Design contract: `docs/implementation_contract/phase3_static_extraction_contract.md`; implementation evidence will require static extraction unit/integration tests and TC-15 runtime policy coverage |
| REQ-012 | SRS Section 14 Static extraction; BA BP-03; BA BR-006 | Static patterns include IF/ELSE, EVALUATE/WHEN, assignment, SQL, procedure refs, status literals, thresholds, role checks, comments near logic. | Output includes extraction method and evidence ranges. | Static Extractor; candidate detail UI | Phase 3 | Planned | Design contract maps every required pattern; implementation evidence will require pattern-specific unit tests and evidence range validation |
| REQ-013 | SRS Section 7 UC-04; SRS Section 11 Analysis jobs; BA BP-03; BA BR-002 | Analysis jobs are asynchronous. | Retry must not create uncontrolled duplicates. | Analysis Orchestrator, Worker, Job Store; analysis job API | Phase 3 | Planned | Design contract defines job/idempotency/retry model; implementation evidence will require TC-02 and worker integration tests |
| REQ-014 | SRS Section 13 AI adapter; Handoff AI adapter boundary; BA Risk 1; BA BR-002, BR-010 | AI-assisted extraction uses provider-independent adapter. | AI cannot access DB directly, write statements, change status, or create review decisions. | AI Adapter, Analysis Orchestrator; adapter config and analysis job API | Phase 5 | Planned | AI boundary unit tests, mandatory mock adapter tests |
| REQ-015 | SRS Section 13 AI adapter; SRS Section 15 Security; BA Risk 1/Risk 5; BA BR-002 | AI output must pass JSON Schema validation. | Invalid output rejected; source minimization and production log redaction required. | AI Adapter, Schema Validation; analysis job API | Phase 5 | Planned | TC-03, log redaction tests |
| REQ-016 | SRS Section 13 AI adapter; Handoff AI boundary; BA BR-002, BR-003 | AI attempt to set `verified` is rejected or coerced to `candidate`. | AI/static extractor only creates candidate; confidence is not review. | Statement Service, AI Adapter validation; analysis job API | Phase 5 | Planned | TC-04 |
| REQ-017 | SRS Section 7 UC-05; SRS Section 10.4 BusinessStatement; BA Object 10.4; BA BR-003 | Candidate statement contains ID, type, title, text, scope, confidence, status, evidence count, unresolved items, extraction method, created metadata. | Confidence is extractor confidence, not a substitute for review. | Statement Service, Candidate UI; statement list/detail APIs | Phase 3 | Planned | Design contract defines candidate schema and UI queue; implementation evidence will require statement schema tests and candidate listing tests |
| REQ-018 | SRS Section 7 UC-05/UC-06; SRS Section 10.4/10.5; BA BP-03; BA BR-006, BR-016 | Each `BusinessStatement` links to at least one evidence range. | No evidence-less `BusinessStatement`; use `AnalysisGap` or `UnresolvedQuestion` when evidence is not sufficient for a statement. | Statement Service, Evidence Service; Candidate detail UI | Phase 3/4 | Planned | Design contract locks candidate evidence invariant and gap/question fallback; implementation evidence will require candidate evidence validation and gap/question schema tests |
| REQ-019 | SRS Section 10.5 Evidence; BA Evidence model; BA BR-006 | Evidence includes file, lines, excerpt, artifact hash, evidence type, relation type, analyst note. | Evidence excerpt cannot be edited as original source; evidence points to artifact hash and source position. | Evidence Service, Storage; Evidence API and detail UI | Phase 2/4 | Planned | Design contract defines Phase 3 evidence schema; implementation evidence will require TC-11 continuation and TC-12 |
| REQ-020 | SRS Section 7 UC-07; BA BP-04/BP-05/BP-06; BA BR-004, BR-005, BR-007, BR-015 | Reviewer can confirm/reject/request evidence/mark conflict/mark obsolete/split/merge with lineage. | Review decisions require reviewer, timestamp, reason, before/after state; merge and obsolete semantics are locked in Phase 0. | Review Service, Statement state machine, Audit; review API and UI | Phase 4 | Planned | Review action integration tests, lineage tests, audit tests |
| REQ-021 | SRS Section 6 Principles; SRS Section 7 UC-07; BA Review decision table; BA BR-001, BR-003 | Only reviewer can verify. | Human promotion gate. | Review Service, RBAC; review API/UI actions | Phase 4 | Planned | TC-05, TC-10 |
| REQ-022 | SRS Section 6 Principles; SRS Section 20 TC-06; BA BR-001 | Verify without valid evidence is blocked. | Verified statement requires at least one valid evidence reference. | Review Service, Evidence validation; review API | Phase 4 | Planned | TC-06 |
| REQ-023 | SRS Section 8.2 Candidate statement; SRS Section 20 TC-07; BA BR-005 | Verified statement cannot be edited directly. | Changes require revision; superseded points to replacement. | Statement Service, Revision Service; revise API | Phase 4 | Planned | TC-07, TC-13 |
| REQ-024 | SRS Section 10.6 ReviewDecision; SRS Section 10.11 AuditEvent; BA BR-004, BR-013 | Review state changes produce `ReviewDecision` and `AuditEvent`. | No deletion of review history; important transitions are audited. | Review Service, Audit; review API and review history UI | Phase 4 | Planned | TC-14, audit history tests |
| REQ-025 | SRS Section 7 UC-09; BA BP-07; BA BR-009 | Conflict records link two or more statements and preserve contradictions until reviewer resolution. | System cannot automatically choose a winner. | Conflict Service; conflict CRUD and workspace UI | Phase 4/6 | Planned | TC-08, conflict resolution tests |
| REQ-026 | SRS Section 7 UC-08; BA Capability 4; BA BR-011 | Glossary terms are project-scoped. | Glossary cannot automatically impose terminology on unreviewed candidates. | Glossary Service; glossary CRUD and UI | Phase 6 | Planned | Glossary CRUD tests, no-auto-apply test |
| REQ-027 | SRS Section 7 UC-10; BA BP-08; BA Acceptance Criteria 7; BA BR-013 | Behavioral test cases are created from verified statements. | Test failure does not automatically invalidate statement; manual/simulated execution only. | Behavioral Test Service; behavioral-test CRUD and manual execution UI | Phase 6 | Planned | Behavioral test CRUD, verified-link validation, manual execution tests |
| REQ-028 | SRS Section 7 UC-12; BA BP-09; BA BR-012 | Every verified rule should have at least one behavioral test or documented exception. | Export readiness warns/blocks according to readiness policy. | Behavioral Test Service, Dashboard, Export validation | Phase 7 | Planned | Dashboard coverage tests, export readiness tests |
| REQ-029 | SRS Section 7 UC-12; BA Risk 6; BA BR-016, BR-017 | Dashboard shows artifact, analysis, statement, conflict, and test coverage metrics. | Do not claim absolute business completeness. | Dashboard Service; dashboard API and UI | Phase 7 | Planned | Dashboard aggregation tests, copy/content review |
| REQ-030 | SRS Section 7 UC-11; SRS Section 19 Acceptance; BA BR-012 | Export ZIP contains required JSON files and schema version. | Export is provider-independent and excludes secrets/credentials. | Export Service; export API and download UI | Phase 7 | Planned | TC-09, secret exclusion tests |
| REQ-031 | SRS Section 7 UC-11; SRS Section 10.11 AuditEvent; BA BR-012, BR-013 | Export creates a consistent snapshot. | Export includes schema version and project snapshot; export action is audited. | Export Service, Audit; export API/UI | Phase 7 | Planned | Snapshot consistency tests, audit-on-export tests |
| REQ-032 | SRS Section 6 Principles; BA BR-010 | Project semantics are isolated. | No cross-customer/project facts; no fine-tuning on customer source. | Domain policy, AI Adapter; backend service boundaries | Phase 1/5 | Partially implemented | Phase 1 stores projects as scoped records and has no cross-project knowledge reuse; AI minimization remains Phase 5 |
| REQ-033 | SRS Section 6 Principles; SRS Section 9 Statement types; BA Uncertainty model; BA BR-008, BR-014, BR-015, BR-016, BR-017 | Preserve exception, unknown, ambiguity, dead-code suspicion, obsolete-but-historic rules. | Rare statements are first-class; suspicion is not conclusion; historically valid statements are not erased. | Statement Service, Conflict, Review; statement detail UI | Phase 3/4/6 | Planned | Design contract defines `AnalysisGap` and `UnresolvedQuestion`; implementation evidence will require unknown/gap/question tests |
| REQ-034 | SRS Section 6 Principles; BA BR-011, BR-018 | No industry best-practice normalization. | External templates are checklists/references only. | Domain policy, Glossary, AI prompt policy; review UI and AI adapter | Phase 3/5/6 | Planned | Negative auto-normalization tests and review checklist |
| REQ-035 | SRS Section 15 Security; Handoff Security gates; BA Risk 5; BA BR-013 | Security controls include upload limit, CORS limits, login/AI rate limiting, secure sessions, password hashing, no source execution, HTML escaping, storage isolation. | All security gates must be tested. | Auth, Ingestion, Source Viewer, AI Adapter, Config | Phase 1/2/5/7 | Partially implemented | Phase 1 auth/session/CSRF/RBAC/CORS/password/rate-limit tests passed; Phase 2 bounded upload limit, ZIP hardening, no execution, source escaping, artifact integrity check, and storage isolation passed; AI/export security remain later |
| REQ-036 | SRS Section 16 Observability; SRS Section 15 Security; BA Risk 5; BA BR-013 | Observability includes structured logs, request ID, job logs, health endpoint, no source content in production error logs. | Logs must not leak source by default. | Observability, API middleware, Worker; health endpoint | Phase 1/5 | Partially implemented | Health endpoint, worker health shell, request ID middleware; production log redaction remains Phase 5 |
| REQ-037 | SRS Section 16 Performance; BA Product KPI; BA BR-016, BR-017 | Performance targets cover pagination, source view latency, upload progress, and async analysis. | MVP must avoid blocking analysis in request path. | API, UI, Worker; statement list, source viewer, upload UI, analysis jobs | Phase 2/3/7 | Partially implemented | Phase 2 bounded 20 MB default upload limit and source viewer smoke covered. Product Owner decision DEC-026 defers 100 MB upload support plus progress UI to Phase 7 or post-MVP while keeping `MAX_UPLOAD_BYTES` environment-configurable. |
| REQ-038 | SRS Section 17 Architecture; SRS Section 18 Project structure; BA Section 20 Constraints; BA BR-010 | MVP runs with Docker Compose and PostgreSQL. | No cloud vendor dependency; local storage abstraction with S3-compatible interface. | DevOps, Infrastructure, Storage; `docker compose up`, `.env.example` | Phase 1 | Implemented | Compose config/build/start smoke; PostgreSQL Alembic migration passed |
| REQ-039 | SRS Section 22 Definition of Done; BA Validation plan; BA BR-013 | README documents setup and demo. | DoD requires API docs and runnable increment. | Documentation; README and OpenAPI docs | Phase 1/7 | Implemented | README added; FastAPI OpenAPI available from running API |
| REQ-040 | SRS Section 19 Acceptance; Handoff first vertical slice; BA Acceptance Criteria; BA BR-001 through BR-013 | First vertical slice reaches login -> project -> upload -> candidate -> evidence -> reviewer verify -> behavioral test -> JSON export. | Must include migration, API, UI, auth, audit, unit/integration/E2E tests. | Cross-module full UI/API path | Phase 1-7 | Partially implemented | Phase 1 E2E covers login -> create project -> project appears in list; Phase 2 E2E covers upload -> inventory -> escaped source viewer |

## Mandatory Test Coverage Map

| Test ID | Required test | Requirement IDs | Planned phase | Status | Acceptance evidence |
|---|---|---|---|---|---|
| TC-01 | ZIP path traversal rejects `../../evil.txt` and writes nothing outside storage root. | REQ-006, REQ-008, REQ-035 | Phase 2 | Implemented | `test_tc01_zip_path_traversal_is_blocked_without_artifacts` |
| TC-02 | Duplicate analysis by artifact hash + analyzer version does not create uncontrolled duplicate candidates. | REQ-013 | Phase 3 | Planned | Worker/orchestrator idempotency test |
| TC-03 | AI invalid JSON/schema output fails validation and writes no candidate. | REQ-014, REQ-015 | Phase 5 | Planned | Mock adapter invalid-output test |
| TC-04 | AI attempts `verified`; backend rejects or coerces to `candidate`. | REQ-014, REQ-016 | Phase 5 | Planned | AI boundary validation test |
| TC-05 | Reviewer confirms candidate with valid evidence; status becomes `verified`. | REQ-021, REQ-022 | Phase 4 | Planned | Review integration test |
| TC-06 | Reviewer confirms candidate without evidence; action is blocked. | REQ-022 | Phase 4 | Planned | Evidence-required verification test |
| TC-07 | Direct edit of verified statement is blocked; revision is required. | REQ-023 | Phase 4 | Planned | Verified edit API test |
| TC-08 | Conflict is preserved and system does not auto-select a winner. | REQ-025 | Phase 4/6 | Planned | Conflict workflow test |
| TC-09 | Export reproducibility for unchanged logical data. | REQ-030, REQ-031 | Phase 7 | Planned | Deterministic export test |
| TC-10 | Viewer cannot call review endpoint; returns 403. | REQ-002, REQ-021, REQ-035 | Phase 1/4 | Implemented | `test_viewer_cannot_create_project_or_call_review_endpoint` |
| TC-11 | Artifact hash is preserved and used in evidence/export. | REQ-009, REQ-019, REQ-030 | Phase 2/7 | Partially implemented | Phase 2 artifact hash preservation and viewer integrity check covered by `test_tc01_text_upload_persists_immutable_inventory_and_escaped_viewer` and `test_tampered_artifact_is_rejected_and_audited`; evidence/export usage remains Phase 4/7 |
| TC-12 | Evidence line ranges are within artifact bounds. | REQ-019 | Phase 2/4 | Planned | Evidence range validation test |
| TC-13 | Revision lineage exists when verified statement is revised/superseded. | REQ-023 | Phase 4 | Planned | Revision lineage test |
| TC-14 | Review action creates ReviewDecision and AuditEvent. | REQ-024 | Phase 4 | Planned | Audit-on-review test |
| TC-15 | Uploaded source is never executed. | REQ-006, REQ-008, REQ-011, REQ-035 | Phase 2/3 | Partially implemented | Ingestion portion covered by `test_unsupported_and_binary_entries_return_warnings_without_execution` and `test_ingestion_module_has_no_dynamic_execution_paths`; extractor runtime policy remains Phase 3 |

## Phase 1 Mandatory E2E Gate

Phase 1 cannot close as `PASS` unless this Playwright flow passes:

1. Login.
2. Create project.
3. Confirm the project appears in the project list.

Result: passed in Phase 1 (`npm run test:e2e`, `1 passed`).

## Phase 2 Browser Gate

Phase 2 added this Playwright flow:

1. Login.
2. Create project.
3. Upload one source file.
4. Confirm artifact appears in inventory.
5. Confirm source viewer renders escaped untrusted content.

Result: passed in Phase 2 (`npm run test:e2e`, `2 passed` total).

## Phase 3 Design Gate

Phase 3 implementation is not authorized until the design PR receives Architect `CLOSED_PASS_DESIGN`.

Design evidence:

- `docs/implementation_contract/phase3_static_extraction_contract.md`

Implementation remains planned for:

- REQ-011 static extraction.
- REQ-012 deterministic patterns.
- REQ-013 async/idempotent analysis jobs.
- REQ-017 candidate statement schema and queue.
- REQ-018 candidate evidence invariant plus gap/question fallback.
- REQ-019 evidence schema continuation.
- REQ-033 uncertainty objects.
- TC-02, TC-12, and TC-15 extraction coverage.

## Security Gate Matrix

| Security gate | Requirement IDs | Enforcement point | Required test |
|---|---|---|---|
| CSRF for cookie sessions | REQ-001, REQ-035 | Auth/session middleware and state-changing routes | CSRF integration test |
| Session invalidation | REQ-001, REQ-035 | Server-side session store | Logout invalidation test |
| Login rate limit | REQ-001, REQ-035 | Auth middleware/storage | Rate limit integration test |
| ZIP path traversal | REQ-008 | Ingestion service before storage write | TC-01 implemented |
| ZIP bomb / decompression ratio | REQ-008, REQ-035 | Ingestion service ZIP scanner | Implemented in Phase 2 decompression ratio regression |
| ZIP symlink/nested archive | REQ-008, REQ-035 | Ingestion service ZIP scanner | Implemented in Phase 2 symlink/nested ZIP regression |
| Binary unsupported handling | REQ-007 | Ingestion classifier | Implemented in Phase 2 binary/unsupported warning regression |
| Filename/storage isolation | REQ-008, REQ-035 | Storage service | Implemented in Phase 2 storage path regression |
| HTML escaping source viewer | REQ-010, REQ-035 | API response/UI rendering | Implemented in Phase 2 API and Playwright source viewer tests |
| Upload limit | REQ-035, REQ-037 | API bounded chunk reader and ingestion service defense-in-depth check | Implemented in Phase 2 oversized upload regression |
| Artifact integrity verification | REQ-009, REQ-035 | Source viewer reads artifact bytes and checks SHA-256 before decoding | Implemented in Phase 2 tampered artifact regression |
| No source execution | REQ-006, REQ-008, REQ-011, REQ-035 | Ingestion/extraction runtime policy | TC-15 ingestion portion implemented; extraction portion remains Phase 3 |
| Password hashing | REQ-001, REQ-035 | Auth service | Hash verification unit test |
| Viewer cannot review | REQ-002, REQ-021 | Backend RBAC | TC-10 |
| Backend RBAC | REQ-002, REQ-035 | API dependencies/application services | RBAC integration suite |
| Secure session cookie | REQ-001, REQ-035 | Cookie/session middleware | Cookie flags/session invalidation test |
| CORS limits | REQ-035 | API middleware | CORS origin test |
| Export excludes secrets | REQ-030, REQ-035 | Export service | Secret exclusion test |
| AI log redaction | REQ-015, REQ-036 | AI adapter/logging | Production log redaction test |

## Current Coverage Status

Phase 2 coverage:

- REQ-001 through REQ-005 are implemented and verified.
- TC-10 is implemented as a backend RBAC gate on the Phase 1 review stub.
- REQ-006 through REQ-009 are implemented and verified for Phase 2.
- REQ-010 is partially implemented: source viewer and escaping are complete; evidence highlighting remains later.
- TC-01 is implemented.
- TC-11 artifact hash preservation is implemented; evidence/export usage remains later.
- TC-15 ingestion no-execution is implemented; extraction no-execution remains Phase 3.
- REQ-037 is partially implemented for Phase 2: bounded upload enforcement and source viewer smoke are covered; 100 MB upload support plus progress UI is formally deferred by DEC-026 to Phase 7 or post-MVP.
- REQ-035, REQ-036, REQ-032, REQ-037, and REQ-040 are partially implemented for their Phase 1/2 subsets.
- REQ-038 and REQ-039 are implemented for Phase 1.
- Extraction, evidence, review, AI, behavioral test, dashboard, and export requirements remain planned.

Phase 3 design coverage:

- Static extraction contract is drafted in `docs/implementation_contract/phase3_static_extraction_contract.md`.
- No Phase 3 implementation code, migration, API, worker, or UI has been added on the design branch.
- Phase 3 implementation is blocked pending Architect `CLOSED_PASS_DESIGN`.
