# Requirements Traceability Matrix

Date: 2026-08-05  
Phase: 0 baseline  
Sources:

- SRS: `docs/01_business_forensics_mvp_requirements.md`
- Business Analysis: `docs/02_business_forensics_mvp_business_analysis.md`
- Handoff: `docs/00_CODEX_HANDOFF_BUSINESS_FORENSICS_MVP.md`

Status legend:

- `Planned`: not implemented yet.
- `Phase 1`: planned for Foundation.
- `Phase 2+`: planned after Foundation.
- `Blocked/Clarify`: requirement needs a decision before implementation can be considered complete.

## End-to-End Matrix

| Requirement ID | Requirement | Business rule / constraint | Module | API / UI | Test |
|---|---|---|---|---|---|
| REQ-001 | User can log in locally. | Password must use Argon2 or bcrypt; login must not reveal whether account exists. | Auth, User, Audit | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, Login UI | Auth integration tests, password hashing unit test, generic login error test, secure session test |
| REQ-002 | Roles exist for `admin`, `analyst`, `reviewer`, `viewer`. | Backend RBAC is authoritative; viewer cannot review. | Auth, RBAC, Domain policy | API auth dependencies; role-aware UI actions | TC-10 / mandatory "Viewer review forbidden"; RBAC unit/integration tests |
| REQ-003 | Admin or analyst can create a project. | One project represents one legacy system scope and one snapshot. Create must audit `PROJECT_CREATED`. | Project Service, Audit | `POST /api/v1/projects`, Project list/create UI | Phase 1 project CRUD integration test, audit-on-create test |
| REQ-004 | Project list/detail/update/archive. | Important project state changes must create audit events. | Project Service, Project state, Audit | `GET/PATCH/POST archive /api/v1/projects...`, Project list/detail UI | Phase 1 CRUD and audit integration tests |
| REQ-005 | Project status supports draft-to-archive lifecycle. | Project may return to analysis when sources are added; state changes are deterministic. | Domain state machine, Project Service | Project API and dashboard status | State transition unit tests, API transition tests |
| REQ-006 | Upload text source files and ZIP packages. | Source is untrusted input; source upload is never executed. | Ingestion Service, Storage | `POST /api/v1/projects/{projectId}/artifacts/upload`, Upload UI | TC-01, no-source-execution test, upload integration tests |
| REQ-007 | Support extensions `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`. | Unsupported/binary files are not silently ignored; warnings are required. | Ingestion Service | Upload API response, inventory UI warnings | Extension allowlist tests, binary unsupported test |
| REQ-008 | ZIP extraction must be safe. | Block path traversal and ZIP bomb; filename must not drive storage path. | Ingestion Security, Storage | Upload API | TC-01 ZIP path traversal, ZIP bomb test, storage isolation test |
| REQ-009 | Artifact inventory records path, type, size, encoding, SHA-256, line count, analysis status, candidate count. | Original artifacts are immutable; evidence must point to artifact hash. | SourceArtifact, Ingestion Service | `GET /api/v1/projects/{projectId}/artifacts`, Source inventory UI | Artifact hash preserved test, inventory integration test |
| REQ-010 | Source content can be viewed with line numbers and evidence highlighting. | Source excerpt and content must be HTML-escaped and treated as untrusted text. | Source Viewer, Evidence UI | `GET /api/v1/projects/{projectId}/artifacts/{artifactId}/content`, Source explorer UI | HTML escaping test, line-range rendering test |
| REQ-011 | Static extraction creates deterministic candidates. | Static extractor only creates `candidate`; no auto-verify. | Extraction, Analysis Orchestrator, Statement Service | `POST /api/v1/projects/{projectId}/analysis-jobs`, Candidate queue UI | Static extraction unit/integration tests |
| REQ-012 | Static patterns include IF/ELSE, EVALUATE/WHEN, assignment, SQL, procedure refs, status literals, thresholds, role checks, comments near logic. | Output must include extraction method and evidence ranges. | Static Extractor | Analysis job API, Candidate detail UI | Pattern-specific unit tests, evidence line range validation |
| REQ-013 | Analysis jobs are asynchronous. | Retry must not create uncontrolled duplicates. | Analysis Orchestrator, Worker, Job Store | `POST/GET /api/v1/projects/{projectId}/analysis-jobs...` | Duplicate analysis idempotency TC-02, worker integration tests |
| REQ-014 | AI-assisted extraction uses provider-independent adapter. | AI cannot access DB directly, write statements, change status, or create review decisions. | AI Adapter, Analysis Orchestrator | Analysis job API, adapter config | AI boundary unit tests, mock adapter tests |
| REQ-015 | AI output must pass JSON Schema validation. | Invalid output rejected; source minimization and log redaction required. | AI Adapter, Schema Validation | Analysis job API | TC-03 AI invalid output, log redaction tests |
| REQ-016 | AI attempt to set `verified` is rejected or coerced to `candidate`. | AI/static extractor only creates candidate. | Statement Service, AI Adapter validation | Analysis job API | TC-04 AI cannot verify |
| REQ-017 | Candidate statement contains ID, type, title, statement text, scope, confidence, status, evidence count, unresolved items, extraction method, created metadata. | Confidence is extractor confidence, not a substitute for review. | Statement Service, Candidate UI | `GET /api/v1/projects/{projectId}/statements`, Candidate queue/detail UI | Statement schema tests, candidate listing tests |
| REQ-018 | Each normal candidate statement links to at least one evidence range. | Evidence before inference; candidate without evidence is unclear except possible `unknown_behavior` conflict requiring clarification. | Statement Service, Evidence Service | Candidate detail UI | Candidate evidence validation tests; clarification needed for `unknown_behavior` |
| REQ-019 | Evidence includes file, lines, excerpt, artifact hash, evidence type, relation type, analyst note. | Evidence excerpt cannot be edited as original source; evidence points to artifact hash and source position. | Evidence Service, Storage | Evidence API, Statement detail UI | Artifact hash test, evidence line range validation TC-12 |
| REQ-020 | Reviewer can confirm/reject/request evidence/mark conflict/mark obsolete/split/merge with lineage. | Review decisions require reviewer, timestamp, reason, before/after state. Manual merge must preserve lineage and scope. | Review Service, Statement state machine, Audit | `POST /api/v1/projects/{projectId}/statements/{statementId}/review`, Statement detail UI | Review action integration tests, lineage tests, audit tests |
| REQ-021 | Only reviewer can verify. | Human promotion gate. | Review Service, RBAC | Review API/UI actions | TC-05 human verify, TC-10 viewer forbidden |
| REQ-022 | Verify without valid evidence is blocked. | Verified statement must have at least one valid evidence. | Review Service, Evidence validation | Review API | TC-06 missing evidence blocked |
| REQ-023 | Verified statement cannot be edited directly. | Changes require revision; superseded must point to replacement. | Statement Service, Revision Service | `POST /api/v1/projects/{projectId}/statements/{statementId}/revise` | TC-07 verified edit blocked, TC-13 revision lineage |
| REQ-024 | Review state changes produce `ReviewDecision` and `AuditEvent`. | No deletion of review history; important transitions are audited. | Review Service, Audit | Review API, Review history UI | TC-14 audit event on review, audit history tests |
| REQ-025 | Conflict records link two or more statements and preserve contradictions until reviewer resolution. | System cannot automatically choose a winner. | Conflict Service | CRUD `/api/v1/projects/{projectId}/conflicts`, Conflict workspace UI | TC-08 conflict preservation, conflict resolution tests |
| REQ-026 | Glossary terms are project-scoped. | Glossary cannot automatically impose terminology on unreviewed candidates. | Glossary Service | CRUD `/api/v1/projects/{projectId}/glossary`, Glossary UI | Glossary CRUD tests, no-auto-apply test |
| REQ-027 | Behavioral test cases are created from verified statements. | Test failure does not automatically invalidate statement; manual/simulated execution only. | Behavioral Test Service | CRUD `/api/v1/projects/{projectId}/behavioral-tests`, execute-manual API/UI | Behavioral test CRUD, verified-link validation, manual execution tests |
| REQ-028 | Every verified rule should have at least one behavioral test or documented exception. | Export readiness must warn/block according to readiness policy. | Behavioral Test Service, Dashboard, Export validation | Dashboard, Export screen | Dashboard coverage tests, export readiness tests |
| REQ-029 | Dashboard shows artifact, analysis, statement, conflict, and test coverage metrics. | Do not claim absolute business completeness. | Dashboard Service | `GET /api/v1/projects/{projectId}/dashboard`, Dashboard UI | Dashboard aggregation tests |
| REQ-030 | Export ZIP contains required JSON files and schema version. | Export is provider-independent and excludes secrets/credentials. | Export Service | `POST /api/v1/projects/{projectId}/exports`, download API/UI | TC-09 export reproducibility, secret exclusion tests |
| REQ-031 | Export creates a consistent snapshot. | Export must include schema version and project snapshot. | Export Service, Audit | Export API/UI | Snapshot consistency tests, audit-on-export tests |
| REQ-032 | Project semantics are isolated. | No cross-customer/project facts; no fine-tuning on customer source. | Domain policy, AI Adapter | Backend service boundaries | Project isolation tests, AI context minimization tests |
| REQ-033 | Preserve exception, unknown, ambiguity, dead-code suspicion, obsolete-but-historic rules. | Rare statements are first-class; suspicion is not conclusion. | Statement Service, Conflict, Review | Candidate/Statement detail UI | Unknown/conflict/obsolete metadata tests |
| REQ-034 | No industry best-practice normalization. | External templates are checklists/references only. | Domain policy, Glossary, AI prompt policy | Review UI, AI adapter | Negative tests for auto-normalization where possible; review checklist |
| REQ-035 | Security controls include upload limit, CORS limits, login/AI rate limiting, secure sessions, password hashing, no source execution, HTML escaping, storage isolation. | All security gates must be tested. | Auth, Ingestion, Source Viewer, AI Adapter, Config | Auth/upload/source/API endpoints | Security regression suite |
| REQ-036 | Observability includes structured logs, request ID, job logs, health endpoint, no source content in production error logs. | Logs must not leak source by default. | Observability, API middleware, Worker | `GET /health` or `/api/v1/health` | Health tests, request ID tests, log redaction tests |
| REQ-037 | Performance targets: 10,000 statement pagination, <2s for source <2MB locally, 100MB upload progress, async analysis. | MVP must avoid blocking analysis in request path. | API, UI, Worker | Statement list, Source viewer, Upload UI, Analysis jobs | Pagination tests, source view perf smoke, upload progress UI test |
| REQ-038 | MVP runs with Docker Compose and PostgreSQL. | No cloud vendor dependency; local storage abstraction with S3-compatible interface. | DevOps, Infrastructure, Storage | `docker compose up`, `.env.example` | Compose smoke test, migration test |
| REQ-039 | README documents setup and demo. | DoD requires API docs and runnable increment. | Documentation | README, generated/open API docs | Documentation review, setup command smoke |
| REQ-040 | First vertical slice reaches login -> project -> upload -> candidate -> evidence -> reviewer verify -> behavioral test -> JSON export. | Must include migration, API, UI, auth, audit, unit/integration/E2E tests. | Cross-module | Full UI/API path | E2E happy path |

## Mandatory Test Coverage Map

| Test ID | Required test | Requirement IDs | Planned phase | Status |
|---|---|---|---|---|
| TC-01 | ZIP path traversal rejects `../../evil.txt` and writes nothing outside storage root. | REQ-006, REQ-008, REQ-035 | Phase 2 | Planned |
| TC-02 | Duplicate analysis by artifact hash + analyzer version does not create uncontrolled duplicate candidates. | REQ-013 | Phase 3 | Planned |
| TC-03 | AI invalid JSON/schema output fails validation and writes no candidate. | REQ-014, REQ-015 | Phase 5 | Planned |
| TC-04 | AI attempts `verified`; backend rejects or coerces to `candidate`. | REQ-014, REQ-016 | Phase 5 | Planned |
| TC-05 | Reviewer confirms candidate with valid evidence; status becomes `verified`. | REQ-021, REQ-022 | Phase 4 | Planned |
| TC-06 | Reviewer confirms candidate without evidence; action is blocked. | REQ-022 | Phase 4 | Planned |
| TC-07 | Direct edit of verified statement is blocked; revision is required. | REQ-023 | Phase 4 | Planned |
| TC-08 | Conflict is preserved and system does not auto-select a winner. | REQ-025 | Phase 4/6 | Planned |
| TC-09 | Export reproducibility for unchanged logical data. | REQ-030, REQ-031 | Phase 7 | Planned |
| TC-10 | Viewer cannot call review endpoint; returns 403. | REQ-002, REQ-021, REQ-035 | Phase 1/4 | Planned |
| TC-11 | Artifact hash is preserved and used in evidence/export. | REQ-009, REQ-019, REQ-030 | Phase 2/7 | Planned |
| TC-12 | Evidence line ranges are within artifact bounds. | REQ-019 | Phase 2/4 | Planned |
| TC-13 | Revision lineage exists when verified statement is revised/superseded. | REQ-023 | Phase 4 | Planned |
| TC-14 | Review action creates ReviewDecision and AuditEvent. | REQ-024 | Phase 4 | Planned |
| TC-15 | Uploaded source is never executed. | REQ-006, REQ-023, REQ-035 | Phase 2 | Planned |

## Security Gate Matrix

| Security gate | Requirement IDs | Enforcement point | Required test |
|---|---|---|---|
| ZIP path traversal | REQ-008 | Ingestion service before storage write | TC-01 |
| ZIP bomb / decompression ratio | REQ-008, REQ-035 | Ingestion service ZIP scanner | ZIP bomb regression |
| Binary unsupported handling | REQ-007 | Ingestion classifier | Binary unsupported regression |
| Filename/storage isolation | REQ-008, REQ-035 | Storage service | Storage path regression |
| HTML escaping source viewer | REQ-010, REQ-035 | API response/UI rendering | XSS/source excerpt regression |
| Upload limit | REQ-035, REQ-037 | API config and reverse proxy/app limit | Upload limit regression |
| No source execution | REQ-006, REQ-035 | Ingestion/extraction runtime policy | TC-15 |
| Password hashing | REQ-001, REQ-035 | Auth service | Hash verification unit test |
| Viewer cannot review | REQ-002, REQ-021 | Backend RBAC | TC-10 |
| Backend RBAC | REQ-002, REQ-035 | API dependencies/application services | RBAC integration suite |
| Login rate limit | REQ-035 | Auth middleware/storage | Rate limit integration test |
| Secure session | REQ-001, REQ-035 | Cookie/session middleware | Cookie flags/session invalidation test |
| CORS limits | REQ-035 | API middleware | CORS origin test |
| Export excludes secrets | REQ-030, REQ-035 | Export service | Secret exclusion test |
| AI log redaction | REQ-015, REQ-036 | AI adapter/logging | Production log redaction test |

## Current Coverage Status

Phase 0 covers planning traceability only:

- Requirements are mapped to modules, API/UI, and test obligations.
- No application requirement is implemented yet.
- No implementation code exists yet.
- Phase 1 will begin with foundation requirements REQ-001 through REQ-005, REQ-035 partial, REQ-036 partial, REQ-038, and REQ-039.

