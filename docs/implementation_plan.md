# Business Forensics Platform MVP Implementation Plan

Date: 2026-08-05
Phase: 0 - Audit, plan, and revision gate
Status: Conditional revision complete; Phase 1 remains blocked until user review approves Phase 0.

Source documents:

- `docs/00_CODEX_HANDOFF_BUSINESS_FORENSICS_MVP.md`
- `docs/01_business_forensics_mvp_requirements.md`
- `docs/02_business_forensics_mvp_business_analysis.md`

## Phase 0 Repository Audit

Current repository state:

- Workspace path: `D:\BIR`
- Existing content before Phase 0: `docs/` only.
- Existing source files before Phase 0: none.
- Existing backend/frontend/worker scaffold before Phase 0: none.
- Existing package manifests before Phase 0: none found (`package.json`, `pyproject.toml`, `requirements.txt` absent).
- Existing Docker Compose file before Phase 0: none found.
- Existing test suite before Phase 0: none found.
- Existing secret/env files before Phase 0: none found.
- Git repository before Phase 0: absent; Git was initialized during Phase 0 to satisfy per-phase commit control.

Local environment observed:

| Tool | Observed version | Phase 1 relevance |
|---|---:|---|
| Python default | 3.13.12 | Do not use as target runtime unless explicitly redirected. |
| Python 3.12 | 3.12.10 via `py -3.12` | Matches required backend runtime. |
| Node.js | v22.22.2 | Suitable for Vite/React tooling. |
| npm | 10.9.7 | Suitable for frontend package management. |
| Docker | 29.1.2 | Suitable for Compose-based MVP. |
| Docker Compose | v2.40.3-desktop.1 | Matches packaging requirement. |
| Git | 2.52.0.windows.1 | Available. |
| ripgrep | 15.2.0 | Available for repository inspection. |

Git evidence known before this revision:

- Phase 0 baseline commit hash: `da2b7dc`
- Phase 0 baseline commit message: `docs: complete phase 0 audit and planning`
- `git log -1 --oneline` before this revision: `da2b7dc docs: complete phase 0 audit and planning`
- `git status --short` before this revision: empty output

Revision commit control:

- This Phase 0 revision must be committed separately.
- Required revision commit message: `docs: complete phase 0 planning and architecture baseline`
- The final revision commit hash and post-commit clean status are reported after the commit is created; a Git commit cannot contain its own final hash without changing that hash.

Phase 0 conclusion:

- This is a blank implementation repository with product documents already present.
- Phase 1 must scaffold the project rather than extend existing application code.
- No implementation code is added in Phase 0 or in this Phase 0 revision.
- Phase 1 must not begin until this revision is reviewed and Phase 0 is explicitly accepted.

## Non-Negotiable Product Invariants

These rules are locked for all phases:

- AI/static extractors only create `candidate` statements.
- Only users with `reviewer` permission can promote a statement to `verified`.
- Every `BusinessStatement` must have at least one evidence reference. If there is no evidence suitable for a statement, create an `AnalysisGap` or `UnresolvedQuestion` instead.
- `unknown_behavior`, if kept as a statement type, must still point to evidence showing an unresolved behavior, such as an unresolved dynamic call, missing procedure source, unclear status code, external program invocation, or unreadable binary dependency.
- Verified statement content cannot be edited in place; changes require a revision with lineage.
- Project semantics are isolated; knowledge from one customer/project cannot be used as fact in another.
- The platform must preserve uncertainty, conflict, exception, and obsolete-but-historic information.
- The system must not apply industry best practice or ontology normalization unless explicitly marked as external reference.
- Uploaded source is untrusted text and must never be executed.
- AI providers are replaceable adapters, not part of the core domain model.
- The mock AI adapter is mandatory. A real provider is optional stretch scope after the mock adapter boundary is proven.
- MVP architecture is a modular monolith, not microservices.
- MVP storage is relational plus local/S3-compatible artifact storage, not a graph database.
- MVP does not build a code translator, BIR runtime, full compiler, or behavioral equivalence engine.
- MVP UI is English-first. Localization is outside Phase 1.
- MVP has no project physical delete API or UI. Archive is the only user-facing removal action; physical deletion is a post-MVP administrative operation.

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
|-- apps
|   |-- api
|   |-- worker
|   `-- web
|-- packages
|   |-- ai_adapters
|   |-- domain
|   |-- export_format
|   |-- extraction
|   `-- schemas
|-- migrations
|-- tests
|   |-- e2e
|   |-- fixtures
|   |-- integration
|   `-- unit
|-- sample_data
|-- docs
|-- docker-compose.yml
|-- .env.example
`-- README.md
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

## Locked Project State Machine

Project creation always starts in `draft`.

Allowed transitions:

| Current state | Allowed next state | Actor | Preconditions |
|---|---|---|---|
| `draft` | `ingesting` | `admin` or `analyst` | A valid source upload request is accepted. |
| `ready_for_analysis` | `ingesting` | `admin` or `analyst` | Additional source upload is accepted; current readiness is invalidated. |
| `review_in_progress` | `ingesting` | `admin` or `analyst` | Additional source upload is accepted; existing reviewed knowledge is retained but current coverage is stale. |
| `export_ready` | `ingesting` | `admin` or `analyst` | Additional source upload is accepted; prior exports remain immutable snapshots but current project readiness is revoked. |
| `ingesting` | previous stable state or `draft` | `system` or `admin` | Ingestion fails or is cancelled. Use recorded `previous_status`; default to `draft` for first upload. |
| `ingesting` | `ready_for_analysis` | `system` | Ingestion completes and source inventory is persisted. |
| `ready_for_analysis` | `analyzing` | `analyst` or `system` | Analysis job is created for at least one ingested artifact. |
| `review_in_progress` | `analyzing` | `analyst` or `system` | Re-analysis is requested for new source, changed analyzer version, or explicit reviewer/analyst reason. |
| `export_ready` | `analyzing` | `analyst` or `system` | Re-analysis is requested without a new upload; current readiness is revoked. |
| `analyzing` | `review_in_progress` | `system` | Analysis job completes and candidates, gaps, or an empty analysis result are persisted. |
| `review_in_progress` | `export_ready` | `reviewer` or `admin` | Export readiness validation passes. |
| Any non-`archived` state | `archived` | `admin` | A non-empty archive reason is supplied and an audit event is written. |
| `archived` | any other state | none | Not allowed in MVP. Archive is irreversible in MVP. |

Invalid transitions and API rules:

- `PATCH /projects/{id}` must not accept arbitrary `status` changes. It may update project metadata only.
- State changes must use explicit application-service commands such as upload accepted, ingestion completed, analysis started, readiness passed, and archive requested.
- Controllers must not encode project state transition rules.
- `archived` projects are read-only except for viewing audit/history/export snapshots.
- Uploading new source after `export_ready` moves the project to `ingesting`, then to `ready_for_analysis` when ingestion completes.
- No project physical deletion API or UI exists in MVP.

## Locked Auth, Session, and CSRF Decision

ADR-002 is accepted for Phase 1 implementation.

Phase 1 auth must use:

- Opaque server-side session IDs, not browser JWT.
- HTTP-only cookie.
- `SameSite=Lax`.
- `Secure=true` in production; local development may use `Secure=false`.
- CSRF token validation for state-changing requests.
- Server-side session invalidation on logout.
- Idle timeout and absolute timeout.
- Development seed user only when `APP_ENV=development`.
- Seed password from environment, never hardcoded.
- Generic login errors.
- Login rate limit keyed by IP and account identifier hash.

## Phase Roadmap

### Phase 0 - Audit, plan, and revision gate

Deliverables:

- Repository and local environment audit.
- Implementation plan.
- Requirements traceability matrix.
- Assumptions/open questions register.
- ADR-001 for MVP architecture.
- ADR-002 for auth/session/CSRF.
- Phase 0 progress/test report with semantic review checklist.
- Phase 0 Git commit evidence.

No implementation code is allowed in this phase.

### Phase 1 - Foundation

Goal:

Create a runnable foundation that supports login, RBAC, project CRUD without physical deletion, health checks, initial schema/migration, audit foundation, worker shell, frontend shell, and CI/local test commands.

Planned deliverables:

- Docker Compose with PostgreSQL 16, Redis, API, worker, and web services.
- Backend scaffold using Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest.
- Frontend scaffold using React, TypeScript strict, Vite, and Playwright.
- Worker scaffold using Dramatiq + Redis.
- Shared domain/schema package layout.
- Initial database migration for `users`, `sessions`, `projects`, and `audit_events`.
- Local auth per ADR-002.
- RBAC roles: `admin`, `analyst`, `reviewer`, `viewer`.
- Backend authorization guards for project CRUD and review-relevant permission checks.
- Project create/list/get/update/archive API and minimal UI.
- Project state transition enforcement in the domain/application layer.
- Health endpoint for API and worker readiness.
- Audit event creation for project creation/update/archive and login-relevant security events where appropriate.
- `.env.example` without secrets.
- README setup instructions.
- Test suite actually executed locally.

Phase 1 tests:

- Unit: role permissions, password hash verification, project state transitions, project status validation, audit event payload shape.
- Integration: health endpoint, login/logout/me, CSRF-protected state-changing requests, project create/list/get/update/archive, backend RBAC denial, session invalidation.
- Migration: Alembic upgrade against PostgreSQL container.
- Frontend: TypeScript build plus basic UI smoke tests.
- E2E: Playwright login -> create project -> project appears in list.

Phase 1 acceptance:

- `docker compose up` starts the local stack.
- API health endpoint responds.
- A seeded development user can log in only when `APP_ENV=development` and the seed password comes from environment.
- Authorized admin/analyst can create a project.
- Viewer cannot perform restricted write/review actions.
- `PATCH /projects/{id}` cannot arbitrarily mutate `status`.
- Project state changes generate audit events.
- Playwright E2E for login -> create project -> project appears in list passes.
- Tests are run, not merely written.
- If Playwright E2E cannot run, Phase 1 must be reported as `CONDITIONAL` or `BLOCKED`, not `PASS`.

### Phase 2 - Secure ingestion

Goal:

Accept source uploads safely and create immutable source inventory.

Key deliverables:

- Upload endpoint for text files and ZIP packages.
- Safe ZIP extraction with path traversal, symlink, nested archive, entry count, ratio, path length, Unicode normalization, and uncompressed size protections.
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
- Candidate, `AnalysisGap`, `UnresolvedQuestion`, and evidence persistence.
- Idempotency by artifact hash + analyzer version.
- Candidate queue UI.

### Phase 4 - Review workflow

Goal:

Implement human review, state transitions, evidence validation, revisions, merge semantics, obsolete handling, and conflict preservation.

Key deliverables:

- Statement state machine in the domain layer.
- `ReviewDecision` persistence for important transitions.
- Evidence validation before verification.
- Reviewer-only verification.
- Required `review_context`: `technical`, `business`, or `combined`.
- Verified revision flow.
- Manual merge as new candidate/revision with lineage and preserved source candidates.
- Conflict creation and statement linking.
- Structured `historical_validity` metadata for suspected obsolete/historic rules.
- Review history UI.
- RBAC and audit coverage.

### Phase 5 - AI adapter

Goal:

Add provider-independent AI-assisted extraction behind strict validation.

Key deliverables:

- AI adapter interface.
- Mock adapter first and mandatory.
- JSON Schema validation for AI output.
- Backend coercion/rejection of any AI attempt to create `verified`.
- Async AI jobs.
- Source minimization and production log redaction.
- One real provider adapter only as optional stretch scope after mock tests pass and without hardcoding provider-specific domain data.

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

- Coverage dashboard that reports evidence coverage, not absolute business completeness.
- Export readiness validation.
- Versioned JSON export ZIP with required files.
- Export reproducibility tests.
- E2E happy path.
- Demo seed package for `Legacy Purchase Approval`.

## Locked Review, Merge, and Obsolete Semantics

Review semantics:

- MVP has one `reviewer` role.
- A valid reviewer decision can verify a statement in MVP.
- Every review decision must include `review_context`: `technical`, `business`, or `combined`.
- Every review decision should also support `confidence_source` as a list of provenance categories such as `source_code`, `sme_interview`, `operating_manual`, `database`, or `runtime_log`.
- A user who has the reviewer role and sufficient domain context may record `combined`.
- Export must include the review context used for each verified statement.
- Export should include `confidence_source` when review decisions provide it.
- MVP does not implement a two-stage approval gate.

Manual merge semantics:

- Merge creates a new candidate or statement revision.
- Source candidates are never deleted.
- Source candidates move to `superseded`.
- The new record stores lineage links to all source candidates and copies evidence as links, not mutable source text.
- Merge is blocked while unresolved scope conflict exists between source candidates.
- Merge by editing one candidate and deleting another is not allowed.

Obsolete handling:

- MVP does not add a new statement status named `obsolete`.
- Suspected obsolete/historic validity is stored as structured metadata:

```json
{
  "historical_validity": {
    "status": "suspected_obsolete",
    "valid_from": null,
    "valid_to": null,
    "reason": "...",
    "review_decision_id": "..."
  }
}
```

- Historically valid statements are not deleted.
- A reviewer decision is required before obsolete metadata affects export/readiness.

## Dependency and Version Policy

- Python dependencies must be pinned through a committed lock file.
- Node dependencies must commit the generated lock file.
- Type checking and linting are CI gates once tooling exists.
- Alembic migrations must not be edited after they have been committed and applied; create a new migration instead.
- `.env` and secrets must not be committed.

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
| Integration | pytest + PostgreSQL/Redis via Compose | API, DB transactions, RBAC, audit, sessions, CSRF |
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
- Project physical deletion API or UI.
