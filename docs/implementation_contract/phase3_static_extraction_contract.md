# Phase 3 Static Extraction Implementation Contract

Date: 2026-08-06
Status: CLOSED_PASS_DESIGN - implementation authorized
Design branch: `phase-3-static-extraction-design`
Implementation branch: `phase-3-static-extraction`

This contract is the approved design baseline for Phase 3 implementation.

## 1. Phase Objective And Out Of Scope

Objective:

- Add deterministic static extraction from ingested immutable source artifacts.
- Split source into deterministic chunks with preserved source line ranges.
- Persist analyzer versions, analysis jobs, candidate `BusinessStatement` records, evidence, `AnalysisGap`, and `UnresolvedQuestion`.
- Move eligible projects through `ready_for_analysis -> analyzing -> review_in_progress`.
- Provide API and UI contracts for creating analysis jobs and browsing the candidate queue.
- Prove idempotency by artifact SHA-256, server-owned analyzer identity, canonical configuration hash, request fingerprint, attempt number, and chunk identity.

Out of scope:

- AI-assisted extraction and AI adapter implementation. Phase 5 owns this.
- Human review, verification, review decisions, revisions, conflict resolution, glossary, behavioral tests, dashboard, and export.
- Full COBOL compiler/parser behavior, execution-order proof, call graph completeness, or behavioral equivalence.
- Source execution, dynamic imports, shell execution, generated target code, or runtime interpretation.
- Auto-merge, auto-normalization, industry ontology, cross-project knowledge reuse, or verified statements.

## 2. Requirement Traceability

| Requirement | Business rule | Module | API/UI | Migration | Required tests |
|---|---|---|---|---|---|
| REQ-011 static extraction | BR-002: static extractor only creates candidate | `packages/extraction`, analysis service, worker | `POST /projects/{projectId}/analysis-jobs`, candidate queue | `0003_phase3_static_extraction` | Pattern unit tests, integration job test, TC-15 extraction no-execution |
| REQ-012 deterministic patterns | BR-006: evidence points to artifact hash and source position | static extractor | statement/evidence detail APIs | source chunks, statements, evidence tables | Pattern-specific tests for every contracted pattern |
| REQ-013 async jobs | Retry must not create uncontrolled duplicates | analysis orchestrator, worker | list/get jobs | analysis jobs and job-artifact links | TC-02 idempotency, retry/failure tests |
| REQ-017 candidate statement schema | BR-003: confidence is not truth | statement service | list/get candidate statements | business statements table | schema validation, list pagination tests |
| REQ-018 every statement has evidence | Phase 0 rule: no evidence-less `BusinessStatement` | statement/evidence service | statement detail and evidence APIs | evidence table with statement FK | candidate without evidence rejected; gap/question used instead |
| REQ-019 evidence model | BR-006: artifact hash and position are mandatory | evidence service | get statement/evidence | evidence table | TC-11 continuation, TC-12 line bounds |
| REQ-033 uncertainty preservation | BR-014, BR-016, BR-017 | gaps/questions service | gaps/questions APIs and UI surfaces | analysis gaps, unresolved questions | gap/question persistence tests |
| REQ-035 security | no source execution, RBAC, CSRF, audit | API dependencies, worker, extraction package | protected job creation | audit and job state | architectural no-execution test, RBAC/CSRF tests |
| REQ-036 observability | job logs without source leakage | analysis service, worker | job status/errors | job error fields and audit payloads | failure logging tests with no source body |
| REQ-040 vertical slice | upload -> deterministic candidate -> evidence | API, UI, worker | E2E candidate generation flow | all Phase 3 tables | Playwright Phase 3 flow |

## 3. Domain Model

`SourceChunk`:

- Deterministic source segment for analysis.
- Belongs to one `SourceArtifact`.
- Preserves `start_line`, `end_line`, immutable chunk text, and content hash.
- May point to a parent chunk when a wider context chunk creates a smaller semantic chunk.

`AnalyzerVersion`:

- Server-owned immutable identity for analyzer name, version, extractor kind, pattern set hash, and canonical configuration hash.
- Defines the pattern set and chunking configuration used for a run.
- A change to analyzer code, pattern definitions, supported configuration keys, normalization, or confidence rules creates a new analyzer version or pattern set hash.
- Clients must not submit `analyzer_name`, `analyzer_version`, or `pattern_set_hash`.

`AnalysisJob`:

- User or system requested analysis run for one project and one server-owned analyzer version/configuration.
- Tracks queued/running/succeeded/failed/cancelled state, shared `request_fingerprint`, per-attempt `attempt_no`, retry lineage, and previous project status.
- Owns job-artifact links and audit events.
- MVP allows only one active analysis job per project, where active means `queued` or `running`.

`BusinessStatement` candidate:

- Natural-language candidate produced by static extraction.
- Phase 3 creates only `status="candidate"`.
- Requires at least one evidence row before commit.
- Stores type, title, statement text, structured expression, scope, confidence, extraction method, analyzer version, analysis job ID, pattern ID, and provenance hash.

`Evidence`:

- Immutable source-backed link from a candidate, gap, or unresolved question to artifact lines.
- Stores analysis job ID, artifact ID, artifact SHA-256 at extraction time, source chunk ID, start/end lines, immutable escaped-safe excerpt text, extraction method, analyzer version, and relation type.

`AnalysisGap`:

- A record that analysis found an important absence, unsupported pattern, missing dependency, unreadable path, or insufficient evidence.
- It is not verified business knowledge and cannot be exported as verified.
- It can have evidence ranges when the gap is caused by observed source.

`UnresolvedQuestion`:

- A question for analyst/reviewer follow-up when source suggests behavior but the business interpretation is unclear.
- May link to a candidate, artifact, chunk, or evidence.
- It is not a statement and cannot be verified directly.

## 4. Detailed Schema

Implementation must create a new Alembic migration named conceptually `0003_phase3_static_extraction`. Existing committed migrations must not be edited.

### `analyzer_versions`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | stable analyzer version ID |
| `analyzer_name` | `String(80)` | no | server-owned non-empty value | index | example `static-cobol-mvp` |
| `analyzer_version` | `String(40)` | no | server-owned semver or date version | index | changes when analyzer code changes |
| `extractor_kind` | `String(32)` | no | `static` in Phase 3 | index | separates future AI/hybrid |
| `configuration_json` | `JSON` | no | server-canonical, allowlisted keys only | none | source of configuration hash |
| `configuration_hash` | `String(64)` | no | SHA-256 hex of canonical config | index | chunk size, overlap, enabled patterns |
| `pattern_set_hash` | `String(64)` | no | server-owned SHA-256 hex | none | identifies deterministic pattern definitions in code |
| `created_at` | `DateTime` | no | UTC | none | immutable creation time |

Uniqueness:

- Unique `(analyzer_name, analyzer_version, configuration_hash)`.

Server ownership:

- API clients cannot set `analyzer_name`, `analyzer_version`, or `pattern_set_hash`.
- The server resolves analyzer identity from deployed code and canonicalizes allowed client configuration before hashing.
- Unknown configuration keys, unsupported pattern IDs, unsafe numeric values, or values outside configured bounds are rejected before job creation.

### `analysis_jobs`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | job ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index `(project_id, status)` | project scope |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | analyzer provenance |
| `status` | `String(32)` | no | `queued`, `running`, `succeeded`, `failed`, `cancelled` | index | job lifecycle |
| `request_fingerprint` | `String(64)` | no | SHA-256 hex | index | shared deterministic identity across retries |
| `requested_by` | `String(36)` | no | FK `users.id` | index | actor |
| `requested_artifact_count` | `Integer` | no | `>= 1` | none | request summary |
| `attempt_no` | `Integer` | no | `>= 1` | none | retry attempt |
| `retry_of_job_id` | `String(36)` | yes | FK `analysis_jobs.id` | index | retry lineage |
| `previous_project_status` | `String(32)` | no | default `ready_for_analysis`; must be a stable non-`analyzing` status | none | failure/cancel recovery |
| `failure_code` | `String(80)` | yes | controlled codes | index optional | failure classification |
| `failure_message` | `Text` | yes | no source body | none | safe diagnostic |
| `created_at` | `DateTime` | no | UTC | index `(project_id, created_at)` | request time |
| `started_at` | `DateTime` | yes | UTC | none | runtime |
| `completed_at` | `DateTime` | yes | UTC | none | runtime |
| `updated_at` | `DateTime` | no | UTC | none | runtime |

Uniqueness and active-job gates:

- Unique `(project_id, request_fingerprint, attempt_no)`.
- At most one active attempt for the same `(project_id, request_fingerprint)`, where active is `queued` or `running`.
- At most one active analysis job per `project_id` in MVP, regardless of artifact selection.
- The active-job rules must be enforced in the application transaction and with partial unique indexes where supported:
  - unique active project index on `project_id` where `status in ('queued', 'running')`;
  - unique active request index on `(project_id, request_fingerprint)` where `status in ('queued', 'running')`.
- If a database backend cannot express a partial unique index portably, application-level transactional checks and concurrency tests are still mandatory.

### `analysis_job_artifacts`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `job_id` | `String(36)` | no | FK `analysis_jobs.id` | composite PK | job scope |
| `artifact_id` | `String(36)` | no | FK `source_artifacts.id` | composite PK, index | artifact scope |
| `artifact_sha256` | `String(64)` | no | copied from artifact at request time | index | immutable source snapshot |
| `status` | `String(32)` | no | `queued`, `running`, `succeeded`, `failed`, `skipped` | index | per-artifact status |
| `created_at` | `DateTime` | no | UTC | none | provenance |

Uniqueness:

- Primary key `(job_id, artifact_id)`.

### `source_chunks`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | chunk ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index | project scope |
| `artifact_id` | `String(36)` | no | FK `source_artifacts.id` | index `(artifact_id, start_line)` | source artifact |
| `analysis_job_id` | `String(36)` | no | FK `analysis_jobs.id` | index | job provenance |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | chunking provenance |
| `chunk_index` | `Integer` | no | deterministic 0-based sequence | unique with artifact/analyzer | ordering |
| `start_line` | `Integer` | no | `>= 1` | index | source range |
| `end_line` | `Integer` | no | `>= start_line` | index | source range |
| `line_count` | `Integer` | no | `>= 1` | none | range length |
| `content` | `Text` | no | immutable text from artifact | none | analysis input snapshot |
| `content_hash` | `String(64)` | no | SHA-256 of normalized chunk text | index | chunk identity |
| `chunk_type` | `String(32)` | no | `line_window`, `paragraph`, `procedure`, `sql_block`, `comment_context` | index | chunk strategy |
| `parent_chunk_id` | `String(36)` | yes | FK `source_chunks.id` | index | lineage for subchunks |
| `created_at` | `DateTime` | no | UTC | none | provenance |

Uniqueness:

- Unique `(analysis_job_id, artifact_id, chunk_index)`.
- Unique `(analysis_job_id, artifact_id, start_line, end_line, content_hash)`.
- Duplicate prevention is scoped to one analysis run; later analysis runs may persist separate chunk rows for the same immutable artifact and analyzer configuration.

### `business_statements`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | statement ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index `(project_id, status)` | project scope |
| `analysis_job_id` | `String(36)` | no | FK `analysis_jobs.id` | index | job provenance |
| `type` | `String(40)` | no | SRS statement type | index | semantic class |
| `pattern_id` | `String(80)` | no | server-supported pattern ID | index | extractor rule provenance |
| `title` | `String(240)` | no | non-empty | text search later | readable label |
| `statement_text` | `Text` | no | non-empty | none | candidate content |
| `structured_expression_json` | `JSON` | yes | object when present | none | machine-readable proposal |
| `scope_json` | `JSON` | no | object, default `{}` | none | scope preserved, not normalized |
| `confidence` | `Float` | no | `0 <= confidence <= 1` | index optional | extractor confidence only |
| `status` | `String(32)` | no | Phase 3 writes only `candidate` | index | review state starts later |
| `extraction_method` | `String(32)` | no | `static` in Phase 3 | index | provenance |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | analyzer provenance |
| `primary_artifact_id` | `String(36)` | no | FK `source_artifacts.id` | index | source provenance |
| `primary_chunk_id` | `String(36)` | no | FK `source_chunks.id` | index | source provenance |
| `candidate_identity_hash` | `String(64)` | no | SHA-256 | unique with analysis job | duplicate prevention |
| `unresolved_count` | `Integer` | no | `>= 0` | none | UI queue metadata |
| `revision_no` | `Integer` | no | default `1` | none | Phase 4 lineage |
| `supersedes_id` | `String(36)` | yes | FK `business_statements.id` | index | Phase 4 lineage placeholder |
| `created_by` | `String(36)` | yes | FK `users.id`; null allowed for system worker | index | actor/system provenance |
| `created_by_kind` | `String(16)` | no | `system` or `user` | index | disambiguates nullable `created_by` |
| `created_at` | `DateTime` | no | UTC | index | provenance |
| `updated_at` | `DateTime` | no | UTC | none | provenance |

Uniqueness:

- Unique `(analysis_job_id, candidate_identity_hash)`.

The uniqueness key prevents duplicate output inside the same deterministic analysis run. It must not auto-merge similar candidates across different scopes, artifacts, analyzer versions, configurations, evidence ranges, or analysis jobs.

Extractor write invariant:

- The static extractor must never `UPDATE`, `UPSERT`, merge into, or mutate an existing `BusinessStatement`.
- Each analysis run may only `INSERT` new candidate `BusinessStatement`, `Evidence`, `AnalysisGap`, and `UnresolvedQuestion` rows for that run.
- If a later run produces the same, replacement, or better candidate, Phase 3 stores it as a separate row with its own `analysis_job_id`.
- Candidate lineage such as `supersedes`, `superseded_by`, revision replacement, or manual merge is Phase 4 review work and must not be implemented by the extractor.

Candidate identity hash inputs:

- Artifact SHA-256.
- Server-owned analyzer name/version.
- Canonical configuration hash.
- `pattern_id`.
- Statement type.
- Canonical scope JSON.
- Canonical structured expression JSON.
- Evidence ranges as sorted `(artifact_sha256, start_line, end_line, relation_type)` tuples.

Natural-language `statement_text` is not a primary identity component. It may be included only as non-authoritative display content so wording/template changes do not create duplicates when the underlying provenance is the same.

Counts:

- Phase 3 does not persist `business_statements.evidence_count`.
- Candidate list/detail APIs return evidence count computed by query or by a transactionally refreshed read model.
- The evidence invariant is enforced by requiring committed evidence rows, not by trusting a statement count column.

### `evidence`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | evidence ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index | project scope |
| `analysis_job_id` | `String(36)` | no | FK `analysis_jobs.id` | index | job provenance |
| `statement_id` | `String(36)` | yes | FK `business_statements.id` | index | candidate target |
| `analysis_gap_id` | `String(36)` | yes | FK `analysis_gaps.id` | index | gap target |
| `unresolved_question_id` | `String(36)` | yes | FK `unresolved_questions.id` | index | question target |
| `artifact_id` | `String(36)` | no | FK `source_artifacts.id` | index | source artifact |
| `artifact_sha256` | `String(64)` | no | copied from artifact | index | integrity provenance |
| `source_chunk_id` | `String(36)` | no | FK `source_chunks.id` | index | chunk provenance |
| `start_line` | `Integer` | no | `>= 1` | index | source range |
| `end_line` | `Integer` | no | `>= start_line` | index | source range |
| `excerpt` | `Text` | no | immutable source excerpt | none | original evidence text |
| `excerpt_sha256` | `String(64)` | no | SHA-256 | none | excerpt integrity |
| `evidence_type` | `String(40)` | no | `source_code`, `sql`, `documentation`, `configuration`, `sample_data`, `manual_observation`, `reviewer_statement` | index | evidence classification |
| `relation_type` | `String(40)` | no | `supports`, `implements`, `contradicts`, `contextualizes`, `suggests`, `references` | index | relationship |
| `extraction_method` | `String(32)` | no | `static` in Phase 3 | index | provenance |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | analyzer provenance |
| `confidence` | `Float` | no | `0 <= confidence <= 1` | none | extractor confidence |
| `status` | `String(32)` | no | `captured` in Phase 3 | index | later validation state |
| `note` | `Text` | yes | analyst/system note, no source beyond excerpt | none | context |
| `created_by` | `String(36)` | yes | FK `users.id` | index | actor/system provenance |
| `created_by_kind` | `String(16)` | no | `system` or `user` | index | disambiguates nullable `created_by` |
| `created_at` | `DateTime` | no | UTC | none | provenance |

Constraints:

- Database check constraint: exactly one of `statement_id`, `analysis_gap_id`, or `unresolved_question_id` must be non-null.
  - Conceptual SQL: `CHECK (((statement_id IS NOT NULL)::int + (analysis_gap_id IS NOT NULL)::int + (unresolved_question_id IS NOT NULL)::int) = 1)`.
  - The Alembic migration must use a portable SQLAlchemy check expression for SQLite/PostgreSQL where possible, plus application validation.
- `start_line` and `end_line` must be within `source_artifacts.line_count`; enforce in application tests because cross-table checks are not portable.

Uniqueness:

- Unique target plus `(artifact_id, start_line, end_line, relation_type, analyzer_version_id)`.

### `analysis_gaps`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | gap ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index `(project_id, status)` | project scope |
| `analysis_job_id` | `String(36)` | no | FK `analysis_jobs.id` | index | job provenance |
| `artifact_id` | `String(36)` | yes | FK `source_artifacts.id` | index | source scope |
| `source_chunk_id` | `String(36)` | yes | FK `source_chunks.id` | index | chunk scope |
| `gap_type` | `String(60)` | no | controlled values | index | e.g. `missing_dependency`, `unsupported_pattern`, `ambiguous_control_flow`, `insufficient_evidence` |
| `title` | `String(240)` | no | non-empty | none | readable label |
| `description` | `Text` | no | non-empty | none | safe text |
| `severity` | `String(20)` | no | `low`, `medium`, `high` | index | triage |
| `status` | `String(32)` | no | `open`, `resolved`, `deferred` | index | gap lifecycle |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | analyzer provenance |
| `identity_hash` | `String(64)` | no | SHA-256 | unique with analysis job | duplicate prevention |
| `created_by` | `String(36)` | yes | FK `users.id` | index | actor/system provenance |
| `created_by_kind` | `String(16)` | no | `system` or `user` | index | disambiguates nullable `created_by` |
| `created_at` | `DateTime` | no | UTC | index | provenance |
| `resolved_at` | `DateTime` | yes | UTC | none | later lifecycle |
| `resolution_note` | `Text` | yes | no verified claim | none | later lifecycle |

### `unresolved_questions`

| Field | Type | Nullable | Constraint | Index/uniqueness | Lineage/provenance |
|---|---|---:|---|---|---|
| `id` | `String(36)` | no | primary key | PK | question ID |
| `project_id` | `String(36)` | no | FK `projects.id` | index `(project_id, status)` | project scope |
| `analysis_job_id` | `String(36)` | no | FK `analysis_jobs.id` | index | job provenance |
| `statement_id` | `String(36)` | yes | FK `business_statements.id` | index | candidate context |
| `artifact_id` | `String(36)` | yes | FK `source_artifacts.id` | index | source context |
| `source_chunk_id` | `String(36)` | yes | FK `source_chunks.id` | index | chunk context |
| `question_type` | `String(60)` | no | controlled values | index | e.g. `scope_ambiguity`, `missing_business_context`, `external_dependency`, `date_semantics` |
| `question_text` | `Text` | no | non-empty | none | analyst-facing question |
| `status` | `String(32)` | no | `open`, `answered`, `deferred` | index | lifecycle |
| `priority` | `String(20)` | no | `low`, `medium`, `high` | index | triage |
| `analyzer_version_id` | `String(36)` | no | FK `analyzer_versions.id` | index | analyzer provenance |
| `identity_hash` | `String(64)` | no | SHA-256 | unique with analysis job | duplicate prevention |
| `created_by` | `String(36)` | yes | FK `users.id` | index | actor/system provenance |
| `created_by_kind` | `String(16)` | no | `system` or `user` | index | disambiguates nullable `created_by` |
| `created_at` | `DateTime` | no | UTC | index | provenance |
| `answered_at` | `DateTime` | yes | UTC | none | later lifecycle |
| `answer_text` | `Text` | yes | no automatic verification | none | later lifecycle |

## 5. State Model

Artifact `analysis_status` values:

- `not_analyzed`: Phase 2 default.
- `queued`: included in a queued analysis job.
- `analyzing`: currently being processed.
- `analyzed`: Phase 3 records persisted successfully for the latest analyzer/config.
- `analysis_failed`: latest job failed for this artifact.
- `analysis_stale`: source artifact remains immutable but project re-analysis made prior coverage stale.

Analysis job states:

- `queued`: DB job created and worker message accepted or ready to be accepted.
- `running`: worker started processing.
- `succeeded`: candidates, gaps/questions, evidence, artifact statuses, and audit committed.
- `failed`: safe failure metadata committed; no partial candidate/evidence from failed transaction remains.
- `cancelled`: reserved for a later explicit cancel action; no UI cancel required in Phase 3.

Project transitions:

- `ready_for_analysis -> analyzing`: analysis job accepted for at least one artifact.
- `review_in_progress -> analyzing`: re-analysis requested for new analyzer/config or explicit analyst reason.
- `export_ready -> analyzing`: allowed by ADR-003, but export readiness is revoked.
- `analyzing -> review_in_progress`: job completes with candidates, gaps/questions, or an empty result.
- `analyzing -> previous_project_status`: job fails or is cancelled, using `AnalysisJob.previous_project_status`.

MVP active-job rule:

- A project may have at most one active analysis job.
- `queued` and `running` are active.
- Creating a new analysis job while any active job exists for the project returns HTTP `409`.
- Project status must not transition away from `analyzing` while an active job remains.
- Worker completion/failure handlers must verify the completing job is the only active job for the project before changing project status.

Failure and retry behavior:

- Phase 3 implementation must update ADR-003 and `packages/domain/project_state.py` with `fail_or_cancel_analysis`.
- `AnalysisJob.previous_project_status` is captured at job creation before the project moves to `analyzing`.
- Allowed previous statuses are `ready_for_analysis`, `review_in_progress`, and `export_ready`.
- Default previous status is `ready_for_analysis` when recovery context is missing.
- Failure/cancel transition is `analyzing -> previous_project_status`.
- Failure/cancel audit event is `ANALYSIS_FAILED_OR_CANCELLED`.
- Because MVP allows only one active job per project, restore is straightforward; still, handlers must check that no other active job remains before restoring.
- Retry creates a new job row with the same `request_fingerprint`, next `attempt_no`, and `retry_of_job_id` pointing to the failed/cancelled job.
- Retrying a succeeded `request_fingerprint` returns or references the existing succeeded result and must not create a new attempt.

## 6. Chunking Contract

Chunking must be deterministic:

- Inputs are artifact bytes decoded through existing Phase 2 encoding metadata after SHA-256 integrity verification.
- The same artifact SHA-256, analyzer version, and configuration hash must produce the same chunk sequence and chunk hashes.
- Chunk indexes are stable 0-based integers ordered by source line.

Line range preservation:

- Each chunk stores `start_line` and `end_line` using source viewer line numbering.
- Chunks must never include lines outside the artifact.
- Evidence ranges must be contained inside at least one stored chunk.

Configurable sizing:

- Required config keys: `chunk_max_lines`, `chunk_overlap_lines`, `max_excerpt_lines`, `enabled_patterns`.
- MVP defaults proposed for implementation: `chunk_max_lines=120`, `chunk_overlap_lines=20`, `max_excerpt_lines=80`.
- Client-supplied configuration must be validated against a server allowlist.
- Numeric values must be clamped or rejected according to server-defined min/max bounds before hashing.
- Unknown keys and unsupported `enabled_patterns` must be rejected.
- Configuration is canonicalized by the server into `configuration_json` and `configuration_hash`.

No semantic loss across boundaries:

- Overlap must preserve context for IF/ELSE, EVALUATE/WHEN, SQL blocks, and comment-adjacent logic near chunk boundaries.
- If a logical block spans beyond max chunk limits, extractor must either create a wider parent chunk within configured hard limits or record an `AnalysisGap` with evidence.
- The extractor must not invent missing lines or infer behavior from a truncated block as if complete.

Idempotency:

- Chunk identity is SHA-256 of normalized line text plus artifact SHA-256, line range, analyzer version ID, and configuration hash.
- Re-running the same analysis must reuse or recreate the same logical chunks without duplicate persisted rows.

## 7. Static Extractor Contract

The static extractor is a deterministic pattern recognizer, not a compiler.

| Pattern | Detection contract | Candidate output | Evidence | Gap/question behavior |
|---|---|---|---|---|
| IF/ELSE | Detect `IF`, comparison operators, optional `ELSE`, and ending markers such as `END-IF` when present. | `decision`, `business_rule`, `validation_constraint`, or `exception` | full condition and affected action lines | create gap for unclosed or cross-chunk condition |
| EVALUATE/WHEN | Detect `EVALUATE`, each `WHEN`, `WHEN OTHER`, and block end. | `decision`, `state_transition`, or `exception` | evaluate line plus selected WHEN block | question when selector meaning is unclear |
| MOVE/COMPUTE/SET | Detect COBOL assignment and calculation statements. | `data_transformation` or `calculation` | assignment line plus adjacent comments | gap when source/target variable is unknown |
| SQL SELECT/INSERT/UPDATE/DELETE | Detect embedded SQL blocks and operation type. | `external_effect`, `state_transition`, `data_transformation`, or `business_rule` | full SQL block and host variables | question for unknown table semantics |
| Procedure/program call | Detect `PERFORM`, `CALL`, procedure references, and program literals. | `external_effect`, `batch_or_schedule_behavior`, or `unknown_behavior` with evidence | call line and surrounding context | gap when target source is missing |
| Status literal | Detect comparisons or assignments involving status/error/result literals. | `state_transition`, `validation_constraint`, or `exception` | status line and action line | question if literal meaning is not inferable |
| Numeric threshold | Detect numeric comparison, range, amount, count, or limit literals. | `business_rule`, `decision`, or `calculation` | comparison and consequence lines | question if unit/currency/scope unclear |
| Date logic | Detect date fields, end-of-month/year, effective date, age, period checks. | `business_rule`, `batch_or_schedule_behavior`, or `exception` | condition and date variable lines | question if calendar/business-day semantics unclear |
| Role/user checks | Detect user, role, auth, permission, branch, department, or group code comparisons. | `authorization_rule` or `decision` | check and consequence lines | question if code-to-role mapping missing |
| Comment-adjacent logic | Attach nearby comments to a candidate only as context. | improves title/scope/note, not standalone truth | code line plus nearby comment lines | gap if comment contradicts code |

Confidence:

- Confidence is extractor confidence only.
- Base confidence must be deterministic by pattern and completeness.
- Adjacent comments can raise context confidence but cannot override source logic.

## 8. Candidate Rules

- Static extractor creates only `candidate`.
- Candidate commit must include at least one evidence row.
- If no valid evidence can be attached, create `AnalysisGap` or `UnresolvedQuestion` instead of `BusinessStatement`.
- `unknown_behavior` is allowed only when evidence shows an unresolved behavior exists.
- Confidence must never imply truth or review approval.
- No auto-merge across candidates.
- No auto-normalization to best practice, industry terms, or inferred target architecture.
- Candidate text must distinguish observed behavior from interpretation.
- Candidate identity hash must be based on project ID, artifact SHA-256, server-owned analyzer version/config, pattern ID, statement type, canonical scope, canonical structured expression, and evidence ranges.
- Natural-language statement wording must not be a primary identity component.

## 9. Evidence Contract

Every evidence row must contain:

- `artifact_id`.
- `artifact_sha256` copied from immutable `SourceArtifact.sha256`.
- `source_chunk_id`.
- `start_line` and `end_line`.
- Immutable `excerpt`.
- `excerpt_sha256`.
- `extraction_method="static"`.
- `analyzer_version_id`.
- `evidence_type` and `relation_type`.

Evidence range rules:

- Range must be inside the artifact line count.
- Range must be inside the linked chunk.
- Excerpt must exactly match artifact lines for the stored range at extraction time.
- Viewer/UI must render excerpts as untrusted text and escape HTML.
- Evidence is immutable. Later analyst notes or validation status changes must not alter excerpt text.

## 10. Idempotency

Idempotency inputs:

- Project ID.
- Sorted artifact IDs and artifact SHA-256 values.
- Server-owned analyzer name.
- Server-owned analyzer version.
- Server-owned pattern set hash.
- Server-canonical configuration hash.
- Chunk identity.

Request fingerprint:

- `request_fingerprint = sha256(project_id + sorted artifact sha256 values + server analyzer name/version + pattern_set_hash + canonical configuration_hash)`.
- The same `request_fingerprint` is reused across retries of the same logical request.
- Each attempt is distinguished by `attempt_no`.
- Unique key: `(project_id, request_fingerprint, attempt_no)`.

Job creation behavior:

- If a job with the same `request_fingerprint` has `succeeded`, return the existing result or job metadata with HTTP `200`.
- If a job with the same `request_fingerprint` is `queued` or `running`, return the existing active job or HTTP `409`; do not enqueue duplicate work.
- If the latest job for the same `request_fingerprint` is `failed` or `cancelled`, create a new attempt with `attempt_no = previous max + 1` and `retry_of_job_id` pointing to the failed/cancelled job.
- Retry never reuses the same unique `(project_id, request_fingerprint, attempt_no)`.

Project-level concurrency:

- If any analysis job for the project is `queued` or `running`, creating another job for that project returns HTTP `409`, even if the new job targets different artifacts or a different request fingerprint.
- Parallel per-artifact analysis is deferred beyond MVP.

Duplicate prevention:

- Chunks use unique artifact/analyzer/range/hash keys.
- Candidates use unique `(analysis_job_id, candidate_identity_hash)`.
- Gaps and unresolved questions use unique `(analysis_job_id, identity_hash)`.
- Cross-run duplicates are retained as separate provenance records; Phase 4 may later add lineage or supersession.
- Evidence uses unique target/range/relation/analyzer keys.

Re-analysis/version behavior:

- New analyzer version or configuration hash can create new candidates for the same artifact.
- Old candidates are not deleted.
- Prior candidates may later become `superseded` only through Phase 4 review/revision rules.
- `source_artifacts.candidate_count` is a transactionally maintained cache for candidate count by primary artifact.
- APIs must not accept direct writes to `candidate_count`.
- Reconciliation tests must compare `source_artifacts.candidate_count` with a query count from `business_statements.primary_artifact_id`.

## 11. API Contract

All mutating endpoints require authenticated session, CSRF token, and backend RBAC.

Create analysis job:

- `POST /api/v1/projects/{projectId}/analysis-jobs`
- Roles: `admin`, `analyst`.
- Server, not client, determines analyzer identity:
  - `analyzer_name`;
  - `analyzer_version`;
  - `pattern_set_hash`;
  - supported configuration keys and bounds.
- Client may only choose artifacts and allowed configuration values.
- Request body:

```json
{
  "artifact_ids": ["optional-artifact-id"],
  "configuration": {
    "chunk_max_lines": 120,
    "chunk_overlap_lines": 20,
    "enabled_patterns": ["if_else", "evaluate_when", "sql"]
  }
}
```

- Unknown configuration keys are rejected.
- Unsupported pattern IDs are rejected.
- Numeric configuration is clamped or rejected according to server min/max rules before canonical hashing.
- Response: `201` for new job, `200` for existing succeeded request fingerprint, or `409` for active duplicate request/project job.
- Response metadata includes server-owned analyzer identity and `request_fingerprint`.

Retry failed/cancelled job:

- `POST /api/v1/projects/{projectId}/analysis-jobs/{jobId}/retry`
- Roles: `admin`, `analyst`.
- Request body: `{}`.
- The target job must belong to the project and have status `failed` or `cancelled`.
- Server creates the next attempt with the same `request_fingerprint`, `attempt_no = previous max + 1`, and `retry_of_job_id = jobId`.
- If any project job is active, response is HTTP `409`.
- If the request fingerprint already has a succeeded attempt, response is HTTP `200` with the succeeded job/result.

List jobs:

- `GET /api/v1/projects/{projectId}/analysis-jobs?status=&limit=&offset=`
- Roles: any authenticated role.
- Must paginate and sort newest first.

Get job:

- `GET /api/v1/projects/{projectId}/analysis-jobs/{jobId}`
- Includes per-artifact status counts, failure metadata, candidate count, gap count, and question count.

List candidate statements:

- `GET /api/v1/projects/{projectId}/statements?status=candidate&type=&artifact_id=&confidence_min=&limit=&offset=`
- Roles: any authenticated role.
- Must paginate.

Get statement/evidence:

- `GET /api/v1/projects/{projectId}/statements/{statementId}`
- `GET /api/v1/projects/{projectId}/statements/{statementId}/evidence`
- Must include source navigation metadata: artifact ID, artifact path, artifact hash, line range, chunk ID.

List gaps/questions:

- `GET /api/v1/projects/{projectId}/analysis-gaps?status=&artifact_id=&limit=&offset=`
- `GET /api/v1/projects/{projectId}/unresolved-questions?status=&artifact_id=&statement_id=&limit=&offset=`

## 12. Candidate Queue UI Contract

Candidate queue must be an operational workspace, not a landing page.

Required controls:

- Project selector integration with existing project workspace.
- Run static analysis action visible for `admin` and `analyst` when project is `ready_for_analysis`, `review_in_progress`, or `export_ready`.
- Filter by statement type, status, artifact/module, confidence range, analyzer version, and unresolved count.
- Pagination for candidate statements.
- Job status panel with queued/running/succeeded/failed states.
- Candidate table columns: title, type, confidence, evidence count, artifact path, line range, analyzer version, updated time.
- Empty states for no source, no analysis run, no candidates, and no gaps/questions.
- Loading states for job creation, job polling, candidate list, and evidence loading.
- Error states for RBAC denial, CSRF failure, job failure, and stale artifact integrity mismatch.
- Source/evidence navigation from candidate row to source viewer line range.

Rendering rules:

- Source excerpts and statement text are untrusted and must be escaped by React default rendering or API-escaped source viewer content.
- Do not use `dangerouslySetInnerHTML` for candidate/evidence text unless content is already API-escaped and audited as such.

## 13. Security

- Source remains untrusted text through chunking, extraction, persistence, and UI.
- No source execution in API, worker, extraction package, tests, or scripts.
- The extraction module must not import or call `subprocess`, `os.system`, `eval`, `exec`, `compile`, `__import__`, `importlib`, or dynamic source loaders.
- Worker must process bytes/text only from immutable artifact storage after SHA-256 verification.
- Job creation requires RBAC `admin` or `analyst`.
- Job creation requires CSRF protection.
- Candidate and evidence viewing requires authentication.
- Audit required for `ANALYSIS_STARTED`, `ANALYSIS_COMPLETED`, and `ANALYSIS_FAILED_OR_CANCELLED`.
- Logs and failure messages must not contain full source text or large excerpts.
- Analysis must not write outside database tables or configured artifact storage.
- Cross-project reads are forbidden; every query must filter by project ID.

## 14. Transaction And Failure Semantics

Job creation transaction:

- Validate project exists and is not archived.
- Reject with HTTP `409` if any `queued` or `running` analysis job already exists for the project.
- Validate project transition to `analyzing`.
- Validate artifact IDs belong to project and have immutable SHA-256.
- Resolve server-owned analyzer name/version and pattern set hash.
- Validate, clamp/reject, and canonicalize client configuration.
- Create/reuse analyzer version using canonical configuration hash.
- Compute `request_fingerprint`.
- If the request fingerprint already has a succeeded job, return it without creating a new job or changing project state.
- If the request fingerprint already has a queued/running job, return it or HTTP `409`.
- If retrying a failed/cancelled request fingerprint, compute `attempt_no = previous max + 1` and set `retry_of_job_id`.
- Create analysis job and job-artifact rows.
- Store `previous_project_status` before changing project status; default to `ready_for_analysis` if missing.
- Update selected artifacts to `queued`.
- Update project to `analyzing`.
- Record `ANALYSIS_STARTED`.
- Commit before worker execution.

Worker success transaction:

- Mark job `running`.
- Confirm this is still the only active analysis job for the project.
- Verify artifact SHA-256 before reading.
- Create chunks, candidates, evidence, gaps, and questions.
- Enforce candidate evidence invariant before commit.
- Update artifact `analysis_status`.
- Recalculate and update `source_artifacts.candidate_count` in the same transaction.
- Do not persist `business_statements.evidence_count`; API evidence counts are computed.
- Mark job `succeeded`.
- Transition project to `review_in_progress`.
- Record `ANALYSIS_COMPLETED`.
- Commit atomically.

Worker failure transaction:

- Roll back partial chunks/candidates/evidence for the failed attempt.
- In a new transaction, mark job `failed`, artifact rows `analysis_failed`, and project back to `AnalysisJob.previous_project_status`.
- Default project recovery target is `ready_for_analysis`.
- Restore project status only after confirming no other active analysis job remains; the MVP active-job rule should make this true, but the check is still mandatory.
- Record `ANALYSIS_FAILED_OR_CANCELLED` with safe failure code/message.
- Preserve prior successful candidates from older jobs.

Retry:

- Only failed/cancelled jobs are retryable.
- Retry must not delete old failed job rows.
- Retry must not duplicate candidates from a previously succeeded identical job.

## 15. Performance Assumptions And Limits

Assumptions:

- MVP runs in a controlled local/Compose environment with low concurrent users.
- Default upload limit remains 20 MB by DEC-026.
- Phase 3 analyzes text artifacts already accepted by Phase 2.
- Source viewer target remains files under 2 MB opening in under 2 seconds locally.

Proposed configurable limits:

- `STATIC_CHUNK_MAX_LINES`, default `120`.
- `STATIC_CHUNK_OVERLAP_LINES`, default `20`.
- `STATIC_MAX_ARTIFACTS_PER_JOB`, default `100`.
- `STATIC_MAX_CANDIDATES_PER_ARTIFACT`, default `500`.
- `STATIC_MAX_EVIDENCE_LINES`, default `80`.
- `STATIC_JOB_TIMEOUT_SECONDS`, default `300`.

Pagination:

- Candidate, job, gap, and question APIs must support `limit` and `offset`.
- Default `limit` should be no more than `50`; maximum should be no more than `200`.

## 16. Migration Plan And Downgrade Behavior

Migration:

- Add `analyzer_versions`.
- Add `analysis_jobs`.
- Add `analysis_job_artifacts`.
- Add `source_chunks`.
- Add `analysis_gaps`.
- Add `unresolved_questions`.
- Add `business_statements`.
- Add `evidence`.
- Add indexes and unique constraints listed in this contract.
- Add DB check constraint on `evidence` so exactly one target FK is non-null.
- Add unique `(project_id, request_fingerprint, attempt_no)` on `analysis_jobs`.
- Add partial unique active-job indexes where supported:
  - one active job per project;
  - one active attempt per `(project_id, request_fingerprint)`.
- Add an index on existing `source_artifacts(project_id, analysis_status)` if supported by the migration target.
- Do not edit `0001_phase1_foundation` or `0002_phase2_source_ingestion`.

Downgrade:

- Drop evidence first.
- Drop business statements.
- Drop unresolved questions.
- Drop analysis gaps.
- Drop source chunks.
- Drop analysis job artifacts.
- Drop analysis jobs.
- Drop analyzer versions.
- Drop added indexes on existing tables.

Downgrade must not delete immutable artifact files from local storage; Alembic downgrade only changes database schema.

## 17. Test Matrix

Unit tests:

- Chunking deterministic for same artifact/config.
- Chunk line ranges and overlap.
- Candidate identity hash stability.
- Candidate identity does not primarily depend on natural-language `statement_text`.
- Evidence range validation.
- Pattern tests for every static extractor rule in section 7.
- Candidate without evidence is rejected.
- Gap/question creation when evidence is insufficient.
- Server-owned analyzer identity is used even when a client attempts to submit analyzer fields.
- Unknown configuration keys and unsupported patterns are rejected.

Integration tests:

- Create analysis job from `ready_for_analysis`.
- Project moves `ready_for_analysis -> analyzing -> review_in_progress`.
- Concurrent job rejection when a project already has a queued/running job.
- Two simultaneous create requests for the same project produce one job and one `409` or existing-job response.
- Artifacts move through queued/analyzing/analyzed.
- Candidate list and statement/evidence detail APIs.
- Gaps/questions APIs.
- RBAC and CSRF for job creation.
- Audit events for analysis start/completion/failure.
- Project status remains `analyzing` while the active job is queued/running.
- Failed/cancelled job restores `previous_project_status`.
- Every candidate, evidence, gap, and question stores `analysis_job_id`.
- `created_by_kind` is `system` for worker-generated rows with nullable `created_by`.

Migration tests:

- SQLite upgrade through `0003_phase3_static_extraction`.
- PostgreSQL Compose upgrade through `0003_phase3_static_extraction`.
- Downgrade from `0003` to `0002` on disposable databases.
- Unique constraints and indexes exist where portable.
- Evidence exactly-one target check rejects invalid rows with zero or multiple target FKs.
- Active-job partial unique indexes are verified on PostgreSQL and SQLite where supported, with application fallback tests.

E2E tests:

- Login -> create project -> upload source -> run static analysis -> candidate appears in queue -> evidence opens source line range.

Idempotency tests:

- TC-02: same artifact hash plus server-owned analyzer version/config does not create duplicate candidates.
- Succeeded request fingerprint returns existing result without creating a new attempt.
- Active duplicate request fingerprint returns conflict or existing active job.
- Different request fingerprint still returns `409` while another project job is active.
- Retry after failed/cancelled attempt creates `attempt_no + 1` with retry lineage.
- Retry does not violate unique `(project_id, request_fingerprint, attempt_no)`.

Provenance tests:

- Evidence stores artifact SHA-256 and exact line range.
- Evidence excerpt matches artifact content at extraction time.
- Candidate links to analysis job, analyzer version, pattern ID, artifact, and source chunk.
- Evidence, gap, and question link to analysis job.
- `source_artifacts.candidate_count` reconciles with candidate query count after success and retry.

Failure/retry tests:

- Simulated extraction exception rolls back partial candidates.
- Failure audit is recorded in a new transaction.
- Project status is restored to `previous_project_status`.
- Project status cannot move out of `analyzing` while an active job remains.

No-execution architectural test:

- AST test covers `packages/extraction`, analysis service, and worker modules for forbidden imports/calls.
- Upload a source snippet containing shell/Python commands and assert no marker side effect is created.

## 18. Acceptance Criteria And Definition Of Done

Phase 3 implementation was authorized after this design received `CLOSED_PASS_DESIGN`.

Phase 3 implementation acceptance:

- All tables and indexes from this contract are implemented by a new migration.
- API can create/list/get analysis jobs.
- API does not accept client-supplied analyzer name/version/pattern set hash.
- Server validates and canonicalizes configuration before creating/reusing analyzer version rows.
- Static analysis runs asynchronously or through the worker boundary without blocking request processing.
- Only one active analysis job per project is possible in MVP.
- Retry uses shared `request_fingerprint` plus incrementing `attempt_no`.
- At least one deterministic candidate is generated from the demo-style source fixture.
- Every candidate has evidence with artifact hash and line range.
- Missing evidence creates `AnalysisGap` or `UnresolvedQuestion`, not an evidence-less statement.
- Every candidate, evidence, gap, and question links to `analysis_job_id`.
- Evidence exactly-one target is enforced by a DB check constraint and application validation.
- `source_artifacts.candidate_count` is transactionally maintained and covered by reconciliation tests.
- TC-02 passes.
- TC-12 line range validation passes.
- TC-15 extraction no-execution portion passes.
- Playwright Phase 3 E2E passes.
- Full pytest, web build, Playwright, SQLite migration, PostgreSQL Compose migration, Compose health checks, and production npm audit are run.
- No Phase 4 review workflow is implemented.

## 19. Open Questions Or Contradictions

No blocking open question remains in this revised contract. Phase 3 implementation received `CLOSED_PASS`; Phase 4 remains not started and will use Epic-based delivery.

| ID | Note | Locked handling | Blocks implementation? |
|---|---|---|---|
| P3-NOTE-001 | Default static analyzer identity needs a concrete implementation constant. | Server owns the identity; implementation should start with `static-cobol-mvp` and `0.1.0` unless Architect requests a naming change. | No |
| P3-NOTE-002 | SourceChunk stores full chunk text, duplicating immutable artifact excerpts. | Accepted for MVP traceability and deterministic replay; revisit compression/storage post-MVP if needed. | No |
| P3-NOTE-003 | SQL parsing depth can expand toward compiler territory. | Keep SQL detection pattern-based and create questions/gaps for unknown semantics. | No |

## 20. Architectural Invariants Affected

Affected and preserved:

- Modular monolith remains the architecture.
- Controllers call services; controllers do not own state transitions.
- Static extractor only creates `candidate`.
- Every `BusinessStatement` requires evidence.
- No evidence produces `AnalysisGap` or `UnresolvedQuestion`.
- Confidence is extractor confidence, not truth.
- Source remains untrusted and is never executed.
- Project semantics remain isolated by `project_id`.
- Review and verification remain Phase 4.
- AI adapter remains Phase 5 and cannot be smuggled into Phase 3.
- No graph database, microservices, code translator, BIR runtime, or behavioral equivalence claim.
- Alembic migration discipline remains: new migration only, no editing committed migrations.
- Analyzer identity and pattern set provenance are server-owned.
- MVP allows one active analysis job per project.
- Retry identity uses `request_fingerprint` plus attempt lineage, not a reused unique idempotency key.
- Analysis failure/cancel restores `previous_project_status` and audits `ANALYSIS_FAILED_OR_CANCELLED`.
- Evidence target integrity is enforced by DB check constraint and application validation.
- Candidate identity is provenance-based and does not primarily depend on natural-language statement text.
- Static extraction is insert-only for candidates, evidence, gaps, and questions; no candidate update, upsert, merge, or lineage mutation is allowed in Phase 3.

Affected and locked by this revision:

- ADR-003 must add `fail_or_cancel_analysis` with `analyzing -> previous_project_status` during Phase 3 implementation.
- `SourceArtifact.analysis_status` gains additional controlled values while remaining a string column.
- The frontend shifts from secure ingestion screen toward an operational analysis/candidate queue, but still uses the existing React/Vite app shell.
