# ADR-001: MVP Architecture

Date: 2026-08-05
Status: Accepted for MVP planning

## Context

Business Forensics Platform MVP must turn legacy source snapshots into candidate business statements with evidence, uncertainty, human review, behavioral tests, and traceable export.

The required constraints are strict:

- AI/static extraction cannot create verified knowledge.
- Reviewer promotion and evidence validation are mandatory.
- Source upload must never be executed.
- Project semantics must remain isolated.
- MVP must not become a code translator, BIR runtime, graph database, or microservice platform.
- Default stack is Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16, Dramatiq + Redis, React/TypeScript/Vite, pytest, Playwright, Docker Compose.

The audited repository has no existing implementation, so the architecture can be established from the documents without migrating legacy app code.

ADR-002 locks the Phase 1 browser auth/session/CSRF design. This ADR delegates those details to ADR-002 rather than leaving cookie-versus-JWT behavior open.

ADR-003 promotes the project lifecycle from planning text into an accepted business contract for implementation and tests.

## Decision

Use a modular monolith with REST API, background worker, relational persistence, and a provider-independent AI adapter boundary.

Logical flow:

```text
Web UI
  -> REST API
  -> Application Services
  -> Domain Layer
  -> PostgreSQL / local file storage / Redis worker queue / AI adapters
```

Repository layout:

```text
apps/api
apps/worker
apps/web
packages/domain
packages/schemas
packages/extraction
packages/ai_adapters
packages/export_format
migrations
tests
sample_data
docs
```

Backend:

- Python 3.12.
- FastAPI for REST API.
- Pydantic v2 for request/response and AI output validation.
- SQLAlchemy 2 for ORM.
- Alembic for migrations.
- PostgreSQL 16 for relational state.
- Dramatiq + Redis for background jobs.

Frontend:

- React.
- TypeScript strict.
- Vite.
- Playwright for E2E.

Storage:

- Local storage abstraction for MVP.
- Generated storage paths independent from user filenames.
- Interface kept compatible with future S3-compatible storage.

Domain rules:

- Statement, evidence, review, project, conflict, and behavioral-test state transitions live in the domain/application layer.
- Controllers call services and cannot own business transitions.
- Project state transitions must follow ADR-003 and the domain implementation in `packages/domain/project_state.py`.
- Review transitions must create `ReviewDecision` and `AuditEvent` for important changes.
- Verification requires reviewer permission and valid evidence.

AI boundary:

- AI adapter receives minimized source chunks and project-local context.
- AI adapter returns structured proposals only.
- Backend validates schema, evidence bounds, confidence, and forces candidate-only semantics.
- AI adapter cannot access DB, write statements, change status, or create review decisions.

Auth/session boundary:

- Phase 1 auth follows ADR-002.
- Browser sessions use opaque server-side session IDs in HTTP-only cookies.
- CSRF protection is mandatory for state-changing requests.
- Logout invalidates the server-side session.

Dependency and migration governance:

- Python dependencies must be pinned through a committed lock file.
- Node dependencies must commit the generated lock file.
- Type checking and linting are CI gates once tooling exists.
- Alembic migrations must not be edited after they have been committed and applied; create a new migration instead.

## Consequences

Positive:

- Keeps MVP small enough to deliver as a runnable vertical slice.
- Preserves testable domain boundaries for evidence, review, and audit rules.
- Avoids premature distributed-system complexity.
- Keeps AI replaceable and prevents provider lock-in.
- Supports traceable export without graph database dependency.

Tradeoffs:

- A modular monolith requires discipline to prevent services/controllers from crossing boundaries.
- Some lineage/conflict queries may be less expressive than a graph model, but are sufficient for MVP.
- Worker/API shared code must be packaged carefully to avoid duplicated domain logic.
- Authentication/session design must be locked early because it affects UI, API, and security tests.
  ADR-002 now locks this design before Phase 1 starts.

## Alternatives Considered

### Microservices

Rejected for MVP. It adds deployment, networking, observability, and transaction complexity while the product risk is still in domain workflow validation.

### Graph database

Rejected for MVP. Conflict and lineage can be represented with relational tables and link tables. A graph database can be reconsidered after MVP if real query needs justify it.

### Code translator / modernization runtime

Rejected. The product purpose is traceable business forensics, not target-code generation or runtime replacement.

### Single TypeScript/NestJS stack

Not selected for this repository because the handoff defines Python 3.12/FastAPI as default and local Python 3.12 is available. This can be revisited only with an explicit team preference before Phase 1 implementation.

## Enforcement

Phase 1 must establish:

- Project layout matching this ADR.
- Domain/service/controller separation.
- Initial migration and audit foundation.
- RBAC, session, CSRF, and auth tests per ADR-002.
- Project state tests per ADR-003.
- Health and Docker Compose smoke tests.

Later phases must add regression tests for:

- Candidate-only extraction.
- Evidence-required verification.
- Revision-only verified edits.
- Conflict preservation.
- AI invalid output and AI `verified` attempts.
- No source execution.
- Export reproducibility.
