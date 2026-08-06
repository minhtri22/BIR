# Epic 4.1 Review Domain Implementation Contract

Date: 2026-08-06
Status: DESIGN_DRAFT - awaiting Architect Review
Branch: `epic-4.1-review-domain-design`

This contract is design-only. It defines the domain semantics for Phase 4 Epic 4.1 and must be reviewed before any implementation code, migration, API route, or UI work starts.

## 1. Objective

Epic 4.1 designs the Review Domain for BIR.

Review Domain exists so a human reviewer can validate whether a candidate `BusinessStatement` reflects business behavior under a specific review context and evidence snapshot.

Review is not an approval workflow. Review is human validation.

The core question is:

> Does this statement accurately reflect observed business behavior under the evidence and context reviewed here?

The allowed high-level reviewer outcomes are:

- Confirm that a statement is accepted under context.
- Reject a statement as inaccurate, out of scope, or unsupported.
- Preserve uncertainty when evidence is insufficient.
- Mark potential duplicate, conflict, or obsolete behavior without deleting history.

`verified` does not mean ground truth. It means reviewed and accepted under a specific context, by a specific reviewer, at a specific time, using a specific immutable evidence snapshot.

## 2. Out Of Scope

Epic 4.1 must not design or implement:

- Approval workflow.
- Workflow engine.
- BPM.
- DMN.
- Notification.
- Assignment.
- Comment thread.
- AI suggestion.
- AI adapter.
- Rule engine.
- Version merge.
- Candidate merge implementation.
- Revision lineage implementation.
- Export.
- Glossary.
- Behavioral test.
- BIR runtime.
- Code translator.
- Runtime execution of source.

The Review Domain may define fields needed for later lineage, conflict, and export provenance, but it must not implement those later behaviors.

## 3. Requirement Traceability

| Requirement | Business rule | Module | API/UI | Migration | Required tests |
|---|---|---|---|---|---|
| REQ-020 review actions | Review decisions require reviewer, timestamp, reason, before/after state, context, and immutable evidence snapshot. | Review Domain, Review Service, Statement state policy | Review decision API, review queue UI, history UI | Future Epic 4.1 migration for review records, decisions, snapshots, sessions, flags, conflict markers | Review action integration tests, state transition tests, immutable history tests |
| REQ-021 only reviewer verifies | Human reviewer is the only actor that can move a candidate to `verified`. | RBAC, Review Service | Create review decision API and decision panel | Reviewer FK on review record; audit actor fields | TC-05, TC-10, reviewer-role tests |
| REQ-022 evidence required for verify | A statement cannot become `verified` unless it has at least one valid evidence snapshot. | Review Service, Evidence Snapshot Service | Decision API validation; evidence viewer | Evidence snapshot table with review record FK | TC-06, evidence snapshot tests |
| REQ-023 verified cannot be edited directly | Review does not mutate statement content. Later changes require revision and lineage. | Statement policy, Review Domain | Statement detail read model; no edit endpoint for verified content | Review outcome records previous and next status only | TC-07, no direct edit tests |
| REQ-024 review audit | Review state changes create immutable review decision history and audit event. | Review Service, Audit | Create decision API, history UI | Review record append-only tables and audit linkage | TC-14, audit-on-review tests |
| REQ-025 conflict preservation | Contradictions and duplicates are marked, not auto-resolved. | Review Flag, Review Conflict Marker | Decision panel and conflict marker display | Conflict marker table, no winner field in Epic 4.1 | TC-08, no auto-winner test |
| REQ-033 uncertainty preservation | `NEEDS_MORE_EVIDENCE` and `UNABLE_TO_DECIDE` preserve uncertainty without pretending it is business knowledge. | Review Flag, Analysis Gap bridge | Pending queue filters and history | Review flags linked to review records | Uncertainty/flag tests |
| REQ-034 no best-practice normalization | Reviewer does not normalize candidates into industry templates in Epic 4.1. | Review Domain policy | Decision panel copy and validation | No glossary/ontology tables | Negative normalization tests and review checklist |
| REQ-035 security | RBAC, CSRF, audit, and no source execution remain mandatory. | API dependencies, Review Service, Audit | State-changing endpoints with CSRF; reviewer-only decisions | Actor and audit fields | RBAC, CSRF, audit, no-execution architectural test |
| REQ-040 vertical slice | Adds reviewer verify step after candidate/evidence. | Review Service and UI | Review queue -> evidence viewer -> decision panel -> history | Review tables | E2E login -> project -> upload -> analysis -> review decision |

## 4. Domain Model

### `ReviewSession`

Reviewer working session for one project and optionally a filtered queue.

Purpose:

- Record when a reviewer began and ended a review pass.
- Group multiple review records created during the same human validation session.
- Provide provenance for review history.

Non-purpose:

- It is not an assignment.
- It is not an exclusive lock.
- It is not a workflow step.
- It does not imply approval authority beyond the authenticated `reviewer` role.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable session identity |
| `project_id` | `String(36)` | no | FK projects | index | review scope |
| `reviewer_user_id` | `String(36)` | no | FK users | index | human reviewer |
| `status` | `String(24)` | no | `active`, `completed`, `cancelled`, `expired` | index | session lifecycle |
| `started_at` | `DateTime` | no | UTC | index | start time |
| `finished_at` | `DateTime` | yes | UTC, required for completed/cancelled/expired | none | finish time |
| `review_context_default` | `String(24)` | yes | `technical`, `business`, `combined`, `manual` | none | default context for decisions |
| `queue_filter_json` | `JSON` | no | server-canonical JSON | none | queue view used by reviewer |
| `created_at` | `DateTime` | no | UTC | none | immutable creation time |

### `ReviewRecord`

Append-only aggregate root for one reviewer action against one `BusinessStatement`.

Purpose:

- Capture reviewer, time, context, decision, reason, evidence snapshot, attachments, confidence, comment, analysis job, statement, and session.
- Provide immutable review history.
- Tie a human decision to a statement state outcome.

Rules:

- `ReviewRecord` is immutable.
- No `UPDATE`.
- A correction creates a new `ReviewRecord`.
- A reviewer command creates a `ReviewRecord`; the review service may update only the statement status as a derived outcome in the same transaction.
- Review never updates statement text, structured expression, scope, original evidence, chunks, artifacts, or analyzer provenance.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable review record |
| `project_id` | `String(36)` | no | FK projects | index | project scope |
| `statement_id` | `String(36)` | no | FK business_statements | index | reviewed candidate/statement |
| `analysis_job_id` | `String(36)` | no | FK analysis_jobs | index | original analysis run provenance |
| `review_session_id` | `String(36)` | yes | FK review_sessions | index | grouped review pass |
| `reviewer_user_id` | `String(36)` | no | FK users | index | human reviewer |
| `reviewer_role` | `String(32)` | no | must include `reviewer` at decision time | none | role snapshot |
| `review_context` | `String(24)` | no | `technical`, `business`, `combined`, `manual` | index | contextual fact boundary |
| `created_at` | `DateTime` | no | UTC | index | decision time |
| `comment` | `Text` | yes | reviewer rationale, not a thread | none | review rationale |
| `confidence` | `Numeric(5,4)` | yes | 0.0000 to 1.0000 | none | reviewer confidence under context |
| `confidence_source_json` | `JSON` | no | array of allowlisted strings | none | source of reviewer confidence |
| `request_fingerprint` | `String(64)` | no | SHA-256 hex of canonical decision command | unique per reviewer command | idempotency for duplicate submits |

Uniqueness:

- Unique `(project_id, reviewer_user_id, request_fingerprint)`.

Idempotency:

- Repeating the same decision request from the same reviewer returns the existing `ReviewRecord`.
- A materially different decision creates a new `ReviewRecord`.
- Idempotency must not become upsert/merge of existing review history.

### `ReviewDecision`

Immutable decision facet attached one-to-one to a `ReviewRecord`.

Allowed `decision_type` values:

- `VERIFY`
- `REJECT`
- `NEEDS_MORE_EVIDENCE`
- `DUPLICATE`
- `OUT_OF_SCOPE`
- `OBSOLETE`
- `UNABLE_TO_DECIDE`

Rules:

- Decision is immutable.
- Decision always has a reason.
- Decision records previous and next statement status.
- Decision confidence is not truth.
- A decision cannot modify candidate content or original evidence.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable decision |
| `review_record_id` | `String(36)` | no | FK review_records | unique | one decision per record |
| `decision_type` | `String(32)` | no | enum allowlist | index | reviewer intent |
| `previous_statement_status` | `String(32)` | no | status before transaction | none | before state |
| `next_statement_status` | `String(32)` | no | derived by state policy | index | after state |
| `outcome_code` | `String(32)` | no | enum allowlist | index | normalized outcome |
| `reason_code` | `String(64)` | no | server allowlist | index | structured reason |
| `reason_text` | `Text` | yes | reviewer detail | none | human rationale |
| `created_at` | `DateTime` | no | UTC | none | immutable decision time |

### `ReviewReason`

Domain value object for why a decision was made.

MVP representation:

- Server allowlisted `reason_code`.
- Optional reviewer `reason_text`.

Examples:

- `matches_source_behavior`
- `missing_evidence`
- `source_contradicts_statement`
- `business_scope_mismatch`
- `duplicate_candidate`
- `obsolete_but_historic`
- `insufficient_context`

Rules:

- `reason_code` is required for every decision.
- `reason_text` is optional but recommended for rejection, obsolete, duplicate, and unable-to-decide outcomes.
- Custom reason catalogs, glossary links, and approval policies are out of scope.

### `ReviewContext`

Domain value object describing the context of human validation.

Allowed values:

- `technical`: reviewer validated against source/code structure.
- `business`: reviewer validated against business/SME understanding.
- `combined`: reviewer used both technical and business context.
- `manual`: reviewer used manually supplied context not represented elsewhere.

Rules:

- Every `ReviewRecord` requires `review_context`.
- Context is part of the verified fact.
- Changing context requires a new `ReviewRecord`.
- Export and later lineage must preserve context.

### `ReviewEvidenceSnapshot`

Immutable copy of evidence at the time of review.

Review must not rely on direct mutable evidence references for history. Even though Phase 3 `Evidence` rows are immutable, review history still stores copied snapshot fields so future display and audit do not depend on mutable joins or changed source viewer behavior.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable snapshot |
| `review_record_id` | `String(36)` | no | FK review_records | index | owner record |
| `source_evidence_id` | `String(36)` | yes | FK evidence, nullable only for manual evidence snapshot | index | original evidence pointer |
| `project_id` | `String(36)` | no | FK projects | index | scope |
| `statement_id` | `String(36)` | no | FK business_statements | index | reviewed statement |
| `analysis_job_id` | `String(36)` | no | FK analysis_jobs | index | analysis provenance |
| `artifact_id` | `String(36)` | no | FK source_artifacts | index | source artifact |
| `artifact_sha256` | `String(64)` | no | SHA-256 hex | index | artifact integrity |
| `source_chunk_id` | `String(36)` | yes | FK source_chunks | index | chunk provenance |
| `start_line` | `Integer` | no | `>= 1` | index pair with artifact | excerpt start |
| `end_line` | `Integer` | no | `>= start_line` | index pair with artifact | excerpt end |
| `excerpt_text` | `Text` | no | immutable copied excerpt | none | source excerpt at review time |
| `excerpt_sha256` | `String(64)` | no | SHA-256 hex | none | snapshot integrity |
| `evidence_type` | `String(48)` | no | copied from source evidence or manual allowlist | none | evidence kind |
| `relation_type` | `String(48)` | no | copied from source evidence or manual allowlist | none | supports/contradicts/context |
| `extraction_method` | `String(80)` | no | copied from evidence | none | extraction provenance |
| `analyzer_version_id` | `String(36)` | no | FK analyzer_versions | index | analyzer provenance |
| `created_at` | `DateTime` | no | UTC | none | snapshot time |

Constraints:

- At least one `ReviewEvidenceSnapshot` is required when `decision_type=VERIFY`.
- Snapshot line ranges must be within artifact bounds.
- Snapshot `artifact_sha256` must equal the artifact hash known at review time.
- Snapshot `excerpt_sha256` is calculated from the stored `excerpt_text`.
- Review cannot update or delete a snapshot.

### `ReviewOutcome`

Domain value object for the result of a decision.

Fields:

- `previous_statement_status`
- `next_statement_status`
- `changed_status`
- `audit_event_type`
- `creates_flag`
- `creates_conflict_marker`
- `requires_evidence_snapshot`

Rules:

- Outcome is derived by server state policy, not by client input.
- Client cannot choose `next_statement_status`.
- Outcome is stored in `ReviewDecision`.
- Outcome does not mean ground truth.

### `ReviewAttachment`

Immutable metadata for external or uploaded material that informed a review decision.

Purpose:

- Preserve optional supporting context such as a manual note file, operating manual excerpt, or SME-provided reference.

Non-purpose:

- It is not a comment thread.
- It is not export implementation.
- It is not source artifact ingestion.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable attachment |
| `review_record_id` | `String(36)` | no | FK review_records | index | owner record |
| `project_id` | `String(36)` | no | FK projects | index | project scope |
| `attachment_kind` | `String(32)` | no | `manual_reference`, `external_document`, `sme_note`, `other` | index | context kind |
| `display_name` | `String(255)` | no | sanitized display only | none | reviewer-facing name |
| `storage_path` | `String(512)` | yes | generated path if binary storage is implemented | unique nullable | immutable storage pointer |
| `sha256` | `String(64)` | yes | required when storage_path present | index | attachment integrity |
| `mime_type` | `String(120)` | yes | server detected | none | content type |
| `size_bytes` | `Integer` | yes | `>= 0` | none | size |
| `created_at` | `DateTime` | no | UTC | none | immutable creation |

Rules:

- If attachment binary upload is deferred, implementation may create metadata-only attachments with no `storage_path`.
- If binary attachment upload is added later, it must use Phase 2 storage isolation and no-execution rules.

### `ReviewFlag`

Append-only marker created by review decisions that preserve uncertainty without changing the statement into a false certainty.

Examples:

- `needs_more_evidence`
- `unable_to_decide`
- `possible_duplicate`
- `possible_conflict`
- `obsolete_suspected`
- `scope_unclear`

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable flag |
| `review_record_id` | `String(36)` | no | FK review_records | index | decision that created flag |
| `project_id` | `String(36)` | no | FK projects | index | scope |
| `statement_id` | `String(36)` | no | FK business_statements | index | flagged statement |
| `flag_type` | `String(48)` | no | enum allowlist | index | uncertainty/marker kind |
| `severity` | `String(16)` | no | `info`, `warning`, `blocking` | index | reviewer impact |
| `message` | `Text` | yes | optional rationale | none | human context |
| `created_at` | `DateTime` | no | UTC | none | immutable creation |

Rules:

- Flags are append-only.
- Clearing or superseding flags is deferred to later revision/lineage semantics and must be represented by new records, not update.
- A flag is not a workflow task.

### `ReviewConflictMarker`

Append-only marker that links a reviewed statement to another statement or unresolved contradiction.

Purpose:

- Preserve possible duplicate/conflict relationships.
- Prevent auto-selection of a winner.
- Provide input for later conflict/revision lineage work.

Core fields:

| Field | Type | Nullable | Constraint | Index/uniqueness | Provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable marker |
| `review_record_id` | `String(36)` | no | FK review_records | index | decision that created marker |
| `project_id` | `String(36)` | no | FK projects | index | scope |
| `statement_id` | `String(36)` | no | FK business_statements | index | primary statement |
| `related_statement_id` | `String(36)` | yes | FK business_statements, same project when present | index | possible duplicate/conflict |
| `marker_type` | `String(48)` | no | `duplicate`, `conflict`, `overlap`, `scope_mismatch` | index | marker kind |
| `description` | `Text` | yes | reviewer rationale | none | human context |
| `created_at` | `DateTime` | no | UTC | none | immutable creation |

Rules:

- No winner field in Epic 4.1.
- No auto-resolution.
- No merge.
- No statement deletion.
- `DUPLICATE` decision creates a marker and leaves lineage changes for Epic 4.4.

## 5. BusinessStatement State Model

The domain recognizes these statement statuses for Phase 4 design:

```text
candidate
verified
rejected
obsolete
superseded
```

Allowed Epic 4.1 transitions:

| Decision | Allowed previous status | Next status | Required evidence snapshot | Notes |
|---|---|---|---:|---|
| `VERIFY` | `candidate` | `verified` | yes, at least one | Human reviewer accepted under context. |
| `REJECT` | `candidate` | `rejected` | recommended, required when evidence exists | Candidate is inaccurate or contradicted. |
| `OUT_OF_SCOPE` | `candidate` | `rejected` | no | Rejected with out-of-scope reason. |
| `NEEDS_MORE_EVIDENCE` | `candidate` | `candidate` | optional | Creates `ReviewFlag`; no false certainty. |
| `UNABLE_TO_DECIDE` | `candidate` | `candidate` | optional | Creates `ReviewFlag`; no false certainty. |
| `DUPLICATE` | `candidate` | `candidate` | optional | Creates `ReviewConflictMarker`; no merge or supersede in Epic 4.1. |
| `OBSOLETE` | `verified` | `obsolete` | yes, at least one | Only verified statements can become obsolete. |

Reserved transitions for later Epic 4.4 revision lineage:

- `verified -> superseded`
- `obsolete -> superseded`
- `rejected -> superseded`, only if Architect approves rejected-candidate lineage use cases

Forbidden transitions:

- `candidate -> obsolete`.
- Any client-selected status transition.
- Any reviewer mutation of statement text, scope, structured expression, extractor confidence, original evidence, or analysis provenance.
- Deleting `rejected`, `obsolete`, or `superseded` statements.

State semantics:

- `candidate`: produced by extractor or later candidate creation flow; not human-verified.
- `verified`: reviewed and accepted under context; not ground truth.
- `rejected`: reviewed and not accepted; preserved for history.
- `obsolete`: was previously verified, then reviewed as no longer current or no longer applicable; preserved as historic knowledge.
- `superseded`: replaced by later revision/lineage; not set by Epic 4.1 implementation.

Concurrency:

- Create decision must lock the target statement row or use an equivalent optimistic precondition.
- Client submits the status observed by the UI.
- If current status differs from the submitted expected status, return HTTP `409` and create no review record.
- Multiple review sessions may view the same queue; decision-time state policy prevents inconsistent status changes.

## 6. Review Decision Rules

`VERIFY`:

- Requires `reviewer` role.
- Requires target status `candidate`.
- Requires at least one valid evidence snapshot.
- Creates immutable `ReviewRecord`, `ReviewDecision`, and `ReviewEvidenceSnapshot` rows.
- Changes statement status to `verified`.
- Audits `STATEMENT_VERIFIED`.

`REJECT`:

- Requires `reviewer` role.
- Requires target status `candidate`.
- Requires reason.
- Changes statement status to `rejected`.
- Does not delete candidate, evidence, gaps, or questions.
- Audits `STATEMENT_REJECTED`.

`NEEDS_MORE_EVIDENCE`:

- Requires `reviewer` role.
- Requires reason.
- Leaves statement status unchanged.
- Creates `ReviewFlag`.
- Does not create verified business knowledge.
- Audited through review completion payload; if Epic 4.5 adds a dedicated event, it must preserve the same record ID.

`DUPLICATE`:

- Requires `reviewer` role.
- Requires reason.
- Leaves statement status unchanged in Epic 4.1.
- Creates `ReviewConflictMarker` when a related statement is supplied.
- Does not merge, supersede, or choose a winner.

`OUT_OF_SCOPE`:

- Requires `reviewer` role.
- Requires reason.
- Changes `candidate -> rejected`.
- Preserves review history and evidence snapshot if provided.
- Audits `STATEMENT_REJECTED`.

`OBSOLETE`:

- Requires `reviewer` role.
- Requires previous status `verified`.
- Requires evidence snapshot or attachment supporting why the accepted statement is no longer current.
- Changes `verified -> obsolete`.
- Audits `STATEMENT_OBSOLETE`.

`UNABLE_TO_DECIDE`:

- Requires `reviewer` role.
- Requires reason.
- Leaves statement status unchanged.
- Creates `ReviewFlag`.
- Does not imply rejection.
- Does not imply verification.

## 7. Evidence Snapshot Contract

Review history must be readable even if later evidence UI, source viewer behavior, or statement lineage changes.

Snapshot creation:

1. Load source `Evidence` rows for the target statement.
2. Verify each referenced artifact still matches stored SHA-256 before snapshot.
3. Copy artifact ID, artifact SHA-256, chunk ID, line range, excerpt, evidence type, relation type, extraction method, analyzer version, and analysis job ID into `ReviewEvidenceSnapshot`.
4. Calculate `excerpt_sha256` from copied excerpt text.
5. Insert snapshots in the same transaction as the review record, decision, audit, and status outcome.

Snapshot immutability:

- No update.
- No delete.
- No lazy recomputation from source evidence.
- Later export/history reads use snapshot values for review provenance.

Manual context:

- Manual attachments may supplement evidence, but cannot replace evidence for `VERIFY` unless a later Architect decision explicitly changes the rule.
- In Epic 4.1, `VERIFY` still requires at least one source-backed evidence snapshot.

## 8. Provenance

Each `ReviewRecord` must be traceable to:

- `Project`.
- `BusinessStatement`.
- `AnalysisJob`.
- `AnalyzerVersion` through evidence snapshot.
- Original candidate evidence through `source_evidence_id` when present.
- Immutable copied evidence snapshot.
- Reviewer user.
- Reviewer role snapshot.
- Review session when present.
- Audit event.

Each candidate, evidence, gap, and unresolved question remains traceable to its Phase 3 `analysis_job_id`. Review adds new provenance; it does not rewrite Phase 3 provenance.

## 9. API Contract

No API implementation is created in this design PR.

All state-changing endpoints require:

- Authenticated session.
- HTTP-only cookie session.
- CSRF token.
- Backend RBAC.
- `reviewer` role for decision creation.
- Audit.

### Start Review Session

`POST /api/v1/projects/{project_id}/review-sessions`

Request:

```json
{
  "review_context_default": "technical",
  "queue_filter": {
    "status": "candidate",
    "artifact_id": null,
    "statement_type": null
  }
}
```

Response: `201` with `ReviewSession`.

Errors:

- `403` if user lacks reviewer role.
- `404` if project is missing.
- `409` if project is archived.

### Finish Review Session

`POST /api/v1/projects/{project_id}/review-sessions/{session_id}/finish`

Request:

```json
{
  "status": "completed"
}
```

Response: `200` with updated session read model.

Rules:

- `completed` or `cancelled` only.
- No review records are modified.
- Audits `REVIEW_COMPLETED` or `REVIEW_CANCELLED`.

### Create Review Decision

`POST /api/v1/projects/{project_id}/statements/{statement_id}/review-decisions`

Request:

```json
{
  "review_session_id": "optional-session-id",
  "expected_statement_status": "candidate",
  "decision_type": "VERIFY",
  "review_context": "combined",
  "reason_code": "matches_source_behavior",
  "reason_text": "Validated against source and SME note.",
  "confidence": 0.86,
  "confidence_source": ["source_code", "sme_interview"],
  "evidence_ids": ["evidence-id-1"],
  "related_statement_id": null,
  "comment": "Accepted for MVP scope."
}
```

Response:

- `201` for a new review record.
- `200` for an idempotent duplicate submit by the same reviewer.

Errors:

- `400` for invalid decision/configuration.
- `403` for insufficient role.
- `404` for missing statement/evidence.
- `409` for stale expected status or invalid state transition.

Server-owned fields:

- `next_statement_status`.
- `outcome_code`.
- Audit payload.
- Snapshot content.
- `request_fingerprint`.

### List Review Queue

`GET /api/v1/projects/{project_id}/review-queue`

Filters:

- `status=candidate|verified|rejected|obsolete|superseded`
- `statement_type`
- `artifact_id`
- `analysis_job_id`
- `has_flags`
- `decision_type`
- `limit`
- `cursor`

Response:

- Paginated statement read models.
- Computed latest review summary.
- Evidence availability summary.
- Flag/conflict marker summary.

### List Pending

`GET /api/v1/projects/{project_id}/review-queue/pending`

Definition:

- Statements with status `candidate`.
- Statements with open uncertainty flags that still require human attention.

### List Verified

`GET /api/v1/projects/{project_id}/statements?status=verified`

Definition:

- Statements accepted under at least one review context.
- API copy must not imply ground truth.

### List Rejected

`GET /api/v1/projects/{project_id}/statements?status=rejected`

Definition:

- Rejected statements are preserved and visible in history.
- API must not hide them by deletion.

### Get Review History

`GET /api/v1/projects/{project_id}/statements/{statement_id}/review-history`

Response:

- Chronological append-only review records.
- Embedded decision.
- Evidence snapshots.
- Attachments metadata.
- Flags and conflict markers created by each decision.
- Audit event IDs when available.

## 10. UI Contract

No UI implementation is created in this design PR.

### Review Queue

The queue must support:

- Candidate list.
- Pending filters.
- Verified list.
- Rejected list.
- Obsolete list when state exists.
- Pagination.
- Filter by statement type, artifact, analysis job, status, and flags.
- Empty, loading, error, and stale-status states.

The UI must avoid language that implies verified equals ground truth.

### Evidence Viewer

The viewer must show:

- Source excerpt.
- Artifact name/display path.
- Artifact SHA-256.
- Line range.
- Analyzer version.
- Analysis job.
- Highlighted evidence lines.

Evidence snapshot display must clearly distinguish:

- Original source evidence.
- Review evidence snapshot.

### Decision Panel

The panel must provide:

- Decision selector for allowed decisions.
- Required reason field.
- Review context selector.
- Confidence input.
- Confidence source selector.
- Evidence selection.
- Related statement selector for duplicate/conflict marker.
- Submit state with CSRF-protected API call.
- Stale status handling after `409`.

The panel must not provide:

- Candidate text edit.
- Evidence edit.
- Auto-merge.
- AI suggestion.
- Approval workflow controls.

### History

History must show:

- Append-only review records.
- Reviewer.
- Time.
- Context.
- Decision.
- Reason.
- Previous/next status.
- Evidence snapshots.
- Attachments metadata.
- Flags and conflict markers.

History must not support delete or edit.

## 11. Audit

Required events:

| Event | Trigger | Payload minimum |
|---|---|---|
| `REVIEW_STARTED` | Review session starts | project_id, review_session_id, reviewer_user_id, context default |
| `REVIEW_COMPLETED` | Session finished or non-state-changing decision recorded | project_id, review_session_id, reviewer_user_id, decision summary when applicable |
| `STATEMENT_VERIFIED` | `VERIFY` changes `candidate -> verified` | project_id, statement_id, review_record_id, reviewer_user_id, evidence_snapshot_count |
| `STATEMENT_REJECTED` | `REJECT` or `OUT_OF_SCOPE` changes `candidate -> rejected` | project_id, statement_id, review_record_id, reviewer_user_id, reason_code |
| `STATEMENT_OBSOLETE` | `OBSOLETE` changes `verified -> obsolete` | project_id, statement_id, review_record_id, reviewer_user_id, reason_code |
| `REVIEW_CANCELLED` | Review session cancelled | project_id, review_session_id, reviewer_user_id |

Audit rules:

- Audit write is atomic with review decision and status outcome.
- Audit payload must not include full source files.
- Audit payload may include short excerpts only through review snapshot IDs, not copied source bodies.
- Failure before commit creates no partial review history.

## 12. Security

Mandatory controls:

- Backend RBAC is authoritative.
- Only users with `reviewer` role can create review decisions.
- Viewer cannot create review decisions.
- Admin/analyst role does not imply reviewer unless explicitly assigned.
- CSRF is required for review session and decision state changes.
- Source remains untrusted text.
- Review never executes source.
- No dynamic import/eval/exec/subprocess path may be introduced by review code.
- Review comments and attachment display names must be escaped in UI.
- Evidence excerpts shown in review UI must remain escaped.
- Audit records every state-changing review action.

Authorization scope:

- User can review only statements within the requested project.
- Evidence IDs must belong to the same project and statement unless the endpoint explicitly supports context evidence.
- Related statement IDs for duplicate/conflict markers must belong to the same project.

## 13. Transaction Semantics

Create review decision transaction:

1. Authenticate and authorize reviewer.
2. Validate CSRF.
3. Load project, statement, analysis job, selected evidence, session.
4. Check statement belongs to project.
5. Check `statement.analysis_job_id` matches the candidate provenance.
6. Lock statement row or validate optimistic status precondition.
7. Validate decision-specific state transition.
8. Verify required evidence and artifact hash.
9. Insert `ReviewRecord`.
10. Insert `ReviewDecision`.
11. Insert `ReviewEvidenceSnapshot` rows.
12. Insert `ReviewAttachment`, `ReviewFlag`, and `ReviewConflictMarker` rows when applicable.
13. Update only `BusinessStatement.status` when the derived outcome changes status.
14. Insert audit event.
15. Commit.

Rollback rules:

- Any failure before commit rolls back all rows and status changes.
- No partial `ReviewRecord` without decision.
- No status change without review record.
- No audit event without review record.
- No review record can be updated after commit.

Concurrency rules:

- Stale UI submissions return `409`.
- Idempotent duplicate submit by the same reviewer returns existing record.
- Concurrent conflicting decisions create at most one status-changing record; the losing transaction receives `409`.

## 14. Migration Contract

This design PR creates no migration.

Future Epic 4.1 implementation migration should add, at minimum:

- `review_sessions`.
- `review_records`.
- `review_decisions`.
- `review_evidence_snapshots`.
- `review_attachments`.
- `review_flags`.
- `review_conflict_markers`.

Expected constraints:

- FK from all review tables to `projects`.
- FK from `review_records.statement_id` to `business_statements`.
- FK from `review_records.analysis_job_id` to `analysis_jobs`.
- FK from `review_records.reviewer_user_id` to `users`.
- Unique one-to-one `review_decisions.review_record_id`.
- Unique idempotency key `(project_id, reviewer_user_id, request_fingerprint)`.
- Check constraints for decision enums, context enums, confidence range, status transitions where DB-portable.
- Snapshot line range check `start_line <= end_line`.
- Attachment storage path unique when present.
- Related statement same-project validation in application service; DB composite FK may be used if supported cleanly.

Downgrade behavior:

- Drop review tables only in reverse dependency order.
- Do not modify Phase 1-3 migrations.
- Do not delete source artifacts, evidence, candidates, analysis jobs, or audit events from earlier phases.

## 15. Test Matrix

Epic 4.1 implementation must define and run tests for:

Unit:

- Decision state policy.
- Review context validation.
- Reason code validation.
- `verified` is contextual fact, not truth terminology in domain labels.
- Request fingerprint canonicalization.
- Evidence snapshot payload creation.

Integration:

- `VERIFY` candidate with evidence -> statement becomes `verified`.
- `VERIFY` without evidence -> blocked.
- `REJECT` preserves statement and evidence.
- `OUT_OF_SCOPE` creates rejected review record.
- `NEEDS_MORE_EVIDENCE` leaves candidate status and creates flag.
- `DUPLICATE` creates conflict marker and does not merge.
- `OBSOLETE` only works from `verified`.
- `candidate -> obsolete` returns `409`.
- Rejected statement is not deleted.
- Review history is append-only.
- Idempotent duplicate review submit returns existing record.
- Concurrent conflicting decision returns one success and one `409`.

Migration:

- Upgrade/downgrade on SQLite.
- Upgrade on PostgreSQL through Compose.
- FK constraints.
- Enum/check constraints.
- Unique idempotency constraint.
- Snapshot line range constraint.

RBAC/Security:

- Reviewer can create decision.
- Viewer cannot create decision.
- Analyst/admin without reviewer role cannot create decision unless explicitly given reviewer role.
- CSRF required.
- Review code no-execution architectural scan for `subprocess`, `os.system`, `eval`, `exec`, and dynamic source execution.
- Comments/display names are escaped in UI/API response.

Immutable review:

- `ReviewRecord` cannot be updated through API.
- `ReviewDecision` cannot be updated through API.
- Evidence snapshots are not recomputed after source evidence changes in tests.
- History cannot be deleted.

State transition:

- Allowed transitions pass.
- Forbidden transitions fail.
- Stale expected status returns `409`.
- Status update, review record, decision, snapshot, and audit are atomic.

Evidence snapshot:

- Snapshot includes artifact ID, artifact SHA-256, line range, excerpt, analyzer version, and analysis job ID.
- Artifact hash mismatch blocks decision.
- Line range out of bounds blocks decision.

Audit:

- `REVIEW_STARTED`.
- `REVIEW_COMPLETED`.
- `STATEMENT_VERIFIED`.
- `STATEMENT_REJECTED`.
- `STATEMENT_OBSOLETE`.
- `REVIEW_CANCELLED`.

E2E:

- Login -> project -> upload -> analysis -> review queue -> verify candidate with evidence -> history shows contextual verification.

## 16. Acceptance Criteria

Design acceptance:

- Contract names every Review Domain object requested for Epic 4.1.
- Contract distinguishes human validation from approval workflow.
- Contract locks `Review != Truth`.
- Contract preserves evidence and history immutability.
- Contract defines allowed and forbidden statement transitions.
- Contract defines API and UI surfaces without implementing them.
- Contract defines test matrix for implementation.
- Contract updates traceability, assumptions, and progress only.

Implementation acceptance for a later PR:

- Migration and code follow this contract.
- All required tests pass.
- E2E review vertical slice passes.
- Phase 4 Epic 4.1 does not add AI, workflow engine, merge, export, glossary, behavioral tests, or runtime.

## 17. Architectural Invariants

New Epic 4.1 invariants:

1. `BusinessStatement` content is never edited by reviewer.
2. Reviewer commands create `ReviewRecord`; the application service may only derive a statement status outcome atomically from that record.
3. Evidence snapshot is immutable.
4. Review does not edit candidate content.
5. Review does not edit original evidence.
6. `ReviewRecord` is append-only.
7. `ReviewDecision` is immutable.
8. Verified does not mean ground truth.
9. Verified means reviewed and accepted under a specific context, by a specific reviewer, at a specific time, using a specific evidence snapshot.
10. Review does not delete history.
11. Rejected, obsolete, and superseded statements remain visible in history.
12. Review does not merge, auto-normalize, or pick conflict winners.
13. Review cannot create verified knowledge without source-backed evidence snapshot.
14. Review must preserve Phase 3 analysis provenance instead of rewriting it.

Existing invariants affected:

- Phase 3 insert-only extractor remains unchanged.
- Phase 3 evidence remains immutable.
- Phase 1 RBAC and CSRF remain authoritative.
- Phase 2 source remains untrusted text.
- Phase 0 no-best-practice-normalization remains in force.
- Phase 0/3 confidence-is-not-truth expands to review-is-not-truth.

## 18. Open Questions Or Contradictions

1. Phase 0 CLAR-010 previously said not to add `obsolete` status in MVP. Epic 4.1 Architect prompt now requires `obsolete` and `superseded` in the statement state model. This contract treats the Epic 4.1 prompt as the newer decision and updates assumptions accordingly, while still preserving historically valid statements.
2. `DUPLICATE` decision creates a marker in Epic 4.1, but actual supersede/merge lineage is deferred to Epic 4.4. Architect should confirm this boundary.
3. `NEEDS_MORE_EVIDENCE` creates a review flag in Epic 4.1. Whether it should also create or link an `AnalysisGap`/`UnresolvedQuestion` is deferred unless Architect requires it now.
4. Attachment binary storage can be implemented using Phase 2 storage rules or deferred as metadata-only. Architect should confirm implementation depth before coding Epic 4.1.
5. Review sessions are non-exclusive in this contract. If exclusive human work queues are desired, that belongs to a later assignment/workflow feature and not Epic 4.1.
6. Confidence scale is numeric 0.0000 to 1.0000 here. Architect should confirm whether reviewer confidence is needed in MVP UI or stored as nullable for later.
7. `OUT_OF_SCOPE` maps to `rejected` status with structured reason. Architect should confirm no separate status is needed.
8. Dedicated audit events for `NEEDS_MORE_EVIDENCE`, `DUPLICATE`, and `UNABLE_TO_DECIDE` are not listed in the prompt. This contract uses review record/history plus `REVIEW_COMPLETED` payload for non-state-changing decisions unless Epic 4.5 adds dedicated events.

