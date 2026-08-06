# ADR-003: Project State Machine

Date: 2026-08-06
Status: Accepted for Phase 1 implementation

## Context

Project lifecycle is a business contract, not only planning text. API behavior, domain services, tests, frontend status display, audit events, and export readiness all depend on the same status semantics.

Phase 0 locked the state machine in `docs/implementation_plan.md`. Phase 1 promotes that lifecycle into this ADR and maps it directly to the domain implementation in `packages/domain/project_state.py`.

## Decision

Project creation always starts in `draft`.

States:

- `draft`
- `ingesting`
- `ready_for_analysis`
- `analyzing`
- `review_in_progress`
- `export_ready`
- `archived`

Allowed transitions:

| Command | Current | Next | Actor | Audit event | Preconditions | Recovery rule | Export impact |
|---|---|---|---|---|---|---|---|
| `accept_source_upload` | `draft` | `ingesting` | `admin`, `analyst` | `SOURCE_UPLOAD_ACCEPTED` | Valid source upload accepted. | None | None |
| `accept_source_upload` | `ready_for_analysis` | `ingesting` | `admin`, `analyst` | `SOURCE_UPLOAD_ACCEPTED` | Additional source upload accepted. | None | Current analysis readiness is stale. |
| `accept_source_upload` | `review_in_progress` | `ingesting` | `admin`, `analyst` | `SOURCE_UPLOAD_ACCEPTED` | Additional source upload accepted. | None | Current review coverage is stale. |
| `accept_source_upload` | `export_ready` | `ingesting` | `admin`, `analyst` | `SOURCE_UPLOAD_ACCEPTED` | Additional source upload accepted. | None | Current readiness is revoked; prior exports remain immutable snapshots. |
| `fail_or_cancel_ingestion` | `ingesting` | previous stable state or `draft` | `system`, `admin` | `INGESTION_FAILED_OR_CANCELLED` | Ingestion fails or is cancelled. | Return to recorded previous stable state; default to `draft`. | None |
| `complete_ingestion` | `ingesting` | `ready_for_analysis` | `system` | `INGESTION_COMPLETED` | Source inventory is persisted. | None | None |
| `start_analysis` | `ready_for_analysis` | `analyzing` | `analyst`, `system` | `ANALYSIS_STARTED` | Analysis job created for at least one artifact. | None | None |
| `start_analysis` | `review_in_progress` | `analyzing` | `analyst`, `system` | `ANALYSIS_STARTED` | Re-analysis requested for new source, analyzer version, or explicit reason. | None | Current review coverage is stale. |
| `start_analysis` | `export_ready` | `analyzing` | `analyst`, `system` | `ANALYSIS_STARTED` | Re-analysis requested without new upload. | None | Current readiness is revoked. |
| `complete_analysis` | `analyzing` | `review_in_progress` | `system` | `ANALYSIS_COMPLETED` | Candidates, gaps, or an empty result are persisted. | None | None |
| `pass_export_readiness` | `review_in_progress` | `export_ready` | `reviewer`, `admin` | `EXPORT_READINESS_PASSED` | Readiness validation passes. | None | Project may export a new snapshot. |
| `archive_project` | any non-`archived` state | `archived` | `admin` | `PROJECT_ARCHIVED` | Non-empty archive reason supplied. | None | Archived project is read-only; prior exports remain immutable. |

Forbidden transitions:

- `archived` to any other state is not allowed in MVP.
- `PATCH /projects/{id}` must not accept arbitrary `status` changes.
- Controllers must not own transition rules.
- AI and workers must not promote projects to readiness without application-service/domain validation.

## Consequences

Positive:

- Domain tests can map 1-to-1 to lifecycle rules.
- API code can reject arbitrary status mutation consistently.
- Audit event expectations are explicit.
- Export behavior after new source upload is deterministic.

Tradeoffs:

- Some future recovery flows, such as unarchive, require a new ADR or explicit revision.
- Ingestion failure recovery needs the previous stable state to be stored when Phase 2 implements upload.

## Enforcement

Phase 1 implements and tests:

- Project creation starts in `draft`.
- Arbitrary status mutation through `PATCH /projects/{id}` is rejected.
- Archive requires `admin`.
- Archive is irreversible and archived projects are read-only.
- Domain transition tests cover allowed and forbidden transitions.

