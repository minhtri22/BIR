# Business Forensics Platform MVP Implementation Plan

Date: 2026-08-05  
Phase: 0 - Audit and plan  
Source documents:

- `docs/00_CODEX_HANDOFF_BUSINESS_FORENSICS_MVP.md`
- `docs/01_business_forensics_mvp_requirements.md`
- `docs/02_business_forensics_mvp_business_analysis.md`

## Phase 0 Repository Audit

Current repository state:

- Workspace path: `D:\BIR`
- Existing content: `docs/` only.
- Existing source files: none.
- Existing backend/frontend/worker scaffold: none.
- Existing package manifests: none found (`package.json`, `pyproject.toml`, `requirements.txt` absent).
- Existing Docker Compose file: none found.
- Existing test suite: none found.
- Existing secret/env files: none found.
- Git state before Phase 0: not initialized as a Git repository.

Local environment observed:

| Tool | Observed version | Phase 1 relevance |
|---|---:|---|
| Python default | 3.13.12 | Do not use as target runtime unless explicitly needed. |
| Python 3.12 | 3.12.10 via `py -3.12` | Matches required backend runtime. |
| Node.js | v22.22.2 | Suitable for Vite/React tooling. |
| npm | 10.9.7 | Suitable for frontend package management. |
| Docker | 29.1.2 | Suitable for Compose-based MVP. |
| Docker Compose | v2.40.3-desktop.1 | Matches packaging requirement. |
| Git | 2.52.0.windows.1 | Available, but repo must be initialized. |
| ripgrep | 15.2.0 | Available for repo inspection. |

Phase 0 conclusion:

- This is effectively a blank implementation repository with product documents already present.
- Phase 1 must scaffold the project rather than extend existing application code.
- Because the workspace was not a Git repository at audit time, Phase 0 will initialize Git before the Phase 0 commit to satisfy the "commit per phase" requirement.
- No implementation code is added in Phase 0.

## Non-Negotiable Product Invariants

These rules are locked for all phases:

- AI/static extractors only create `candidate` statements.
- Only users with `reviewer` permission can promote a statement to `verified`.
- A verified statement must have at least one valid evidence record.
- Verified statement content cannot be edited in place; changes require a revision with lineage.
- Project semantics are isolated; knowledge from one customer/project cannot be used as fact in another.
- The platform must preserve uncertainty, conflict, exception, and obsolete-but-historic information.
- The system must not apply industry best practice or ontology normalization unless explicitly marked as external reference.
- Uploaded source is untrusted text and must never be executed.
- AI providers are replaceable adapters, not part of the core domain model.
- MVP architecture is a modular monolith, not microservices.
- MVP storage is relational plus local/S3-compatible artifact storage, not a graph database.
- MVP does not build a code translator, BIR runtime, full compiler, or behavioral equivalence engine.

## Target MVP Architecture

The MVP will use a modular monolith:

```text
Web UI
  -> REST API
  -> Application Services
  -> Domain Layer
  -> PostgreSQL / file storage / worker / AI adapters
```

Proposed repository structure:

```text
D:\BIR
├── apps
│   ├── api
│   ├── worker
│   └── web
├── packages
│   ├── ai_adapters
│   ├── domain
│   ├── export_format
│   ├── extraction
│   └── schemas
├── migrations
├── tests
│   ├── e2e
│   ├── fixtures
│   ├── integration
│   └── unit
├── sample_data
├── docs
├── docker-compose.yml
├── .env.example
└── README.md
```

Application boundaries:

| Layer | Responsibility | Must not do |
|---|---|---|
| UI | Human workflows, source viewing, review actions, dashboards | Enforce trusted business state alone |
| REST API controllers | Request parsing, auth dependency wiring, response mapping | Own business state transitions |
| Application services | Transaction orchestration, authorization checks, audit emission | Let AI mutate state directly |
| Domain layer | State machines, evidence rules, review rules, invariants | Depend on FastAPI, DB sessions, or AI providers |
| Infrastructure | PostgreSQL, storage, job queue, AI adapter implementations | Encode business approval shortcuts |
| Worker | Async ingestion/analysis/export jobs | Promote statements to `verified` |

## Phase Roadmap

### Phase 0 - Audit and plan

Deliverables:

- Repository and local environment audit.
- Implementation plan.
- Requirements traceability matrix.
- Assumptions/open questions register.
- ADR-001 for MVP architecture.
- Phase 0 progress/test report.
- Phase 0 Git commit.

No implementation code is allowed in this phase.

### Phase 1 - Foundation

Goal:

Create a runnable foundation that supports login, RBAC, project CRUD, health checks, initial schema/migration, audit foundation, worker shell, frontend shell, and CI/local test commands.

Planned deliverables:

- Docker Compose with PostgreSQL 16, Redis, API, worker, and web services.
- Backend scaffold using Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest.
- Frontend scaffold using React, TypeScript strict, Vite, and Playwright.
- Worker scaffold using Dramatiq + Redis.
- Shared domain/schema package layout.
- Initial database migration for `users`, `projects`, and `audit_events`.
- Local auth with secure password hashing and HTTP-only session cookie unless locked otherwise.
- RBAC roles: `admin`, `analyst`, `reviewer`, `viewer`.
- Backend authorization guards for project CRUD and review-relevant permission checks.
- Project CRUD API and minimal UI.
- Health endpoint for API and worker readiness.
- Audit event creation for project creation/update/archive and login-relevant security events where appropriate.
- `.env.example` without secrets.
- README setup instructions.
- Test suite actually executed locally.

Phase 1 tests:

- Unit: role permissions, password hash verification, project status validation, audit event payload shape.
- Integration: health endpoint, login/logout/me, project create/list/get/update/archive, backend RBAC denial.
- Migration: Alembic upgrade against PostgreSQL container.
- Frontend: TypeScript build plus basic UI smoke tests.
- E2E: login and create project happy path if the dev stack is stable within Phase 1.

Phase 1 acceptance:

- `docker compose up` starts the local stack.
- API health endpoint responds.
- A seeded or created user can log in.
- Authorized admin/analyst can create a project.
- Viewer cannot perform restricted write/review actions.
- Project state changes generate audit events.
- Tests are run, not merely written.

### Phase 2 - Secure ingestion

Goal:

Accept source uploads safely and create immutable source inventory.

Key deliverables:

- Upload endpoint for text files and ZIP packages.
- Safe ZIP extraction with path traversal, symlink, nested archive, entry count, ratio, and uncompressed size protections.
- Configurable upload limits.
- Extension allowlist for `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`.
- Binary/unsupported file warning flow.
- SHA-256, encoding detection, line count, immutable storage path, inventory API.
- Source viewer UI with line numbers and safe HTML escaping.
- Audit events for upload/ingest.

### Phase 3 - Static extraction

Goal:

Generate deterministic candidates with evidence ranges without AI dependency.

Key deliverables:

- Source chunking.
- Static analyzer versioning.
- Pattern extraction for IF/ELSE, EVALUATE/WHEN, assignments, SQL, procedure calls, status literals, thresholds, date logic, role/user checks, and comment-adjacent logic.
- Candidate and evidence persistence.
- Idempotency by artifact hash + analyzer version.
- Candidate queue UI.

### Phase 4 - Review workflow

Goal:

Implement human review, state transitions, evidence validation, revisions, and conflict preservation.

Key deliverables:

- Statement state machine in the domain layer.
- `ReviewDecision` persistence for important transitions.
- Evidence validation before verification.
- Reviewer-only verification.
- Verified revision flow.
- Conflict creation and statement linking.
- Review history UI.
- RBAC and audit coverage.

### Phase 5 - AI adapter

Goal:

Add provider-independent AI-assisted extraction behind strict validation.

Key deliverables:

- AI adapter interface.
- Mock adapter first.
- JSON Schema validation for AI output.
- Backend coercion/rejection of any AI attempt to create `verified`.
- Async AI jobs.
- Source minimization and production log redaction.
- One real provider adapter only after mock tests pass and without hardcoding provider-specific domain data.

### Phase 6 - Conflict, glossary, behavioral tests

Goal:

Complete knowledge-management workflows after review.

Key deliverables:

- Project-scoped glossary CRUD.
- No automatic glossary application to unreviewed candidates.
- Conflict workspace and resolution reasons.
- Behavioral test CRUD linked to verified statements/evidence.
- Manual execution recording.
- Traceability updates.

### Phase 7 - Dashboard and export

Goal:

Provide the demonstrable end-to-end MVP package.

Key deliverables:

- Coverage dashboard.
- Export readiness validation.
- Versioned JSON export ZIP with required files.
- Export reproducibility tests.
- E2E happy path.
- Demo seed package for `Legacy Purchase Approval`.

## MVP Vertical Slice Order

The first complete slice must be built in this order:

1. Login.
2. Create project.
3. Upload one source file.
4. Generate one deterministic candidate.
5. Show evidence.
6. Reviewer verifies.
7. Create behavioral test.
8. Export JSON.

Every slice increment must include migration, API, UI, authorization, audit, unit test, integration test, and E2E coverage where applicable.

## Test Strategy

Test levels:

| Level | Tool | Scope |
|---|---|---|
| Unit | pytest / frontend unit runner if added | Domain rules, validators, utility functions |
| Integration | pytest + PostgreSQL/Redis via Compose | API, DB transactions, RBAC, audit |
| E2E | Playwright | Critical user flows |
| Build/type | Python tooling, TypeScript strict, Vite build | Static correctness |
| Security regression | pytest integration tests | Upload, auth, RBAC, source rendering, AI boundary |

Mandatory tests tracked in `docs/requirements_traceability.md`:

- ZIP path traversal.
- ZIP bomb.
- Duplicate analysis idempotency.
- AI invalid output.
- AI attempts `verified`.
- Human verify with evidence.
- Verify without evidence blocked.
- Verified direct edit blocked.
- Conflict preservation.
- Export reproducibility.
- Viewer review forbidden.
- Artifact hash preserved.
- Evidence line range validation.
- Revision lineage.
- Audit event on review.
- No source execution.

## Phase Reporting Template

After each phase, update:

- `docs/progress.md`
- `docs/requirements_traceability.md`
- `docs/assumptions.md`
- Phase test report.
- Known limitations.
- Git status.

Report to user:

- Files created or modified.
- Commands run.
- Test result.
- Requirements covered.
- Limitations.
- New assumptions.
- Next phase.

## Explicit MVP Exclusions

The following must not be introduced during MVP implementation:

- Code translator.
- BIR runtime.
- Graph database.
- Microservices.
- Production mainframe integration.
- Full compiler/parser for COBOL/RPG/PL/I/Oracle Forms.
- Behavioral equivalence proof engine.
- Industry ontology or automatic business normalization.
- Cross-customer learning or fine-tuning on customer source.
- Source upload execution.
- Hardcoded AI provider dependency.

