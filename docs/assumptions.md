# Assumptions, Open Questions, and MVP Risk Register

Date: 2026-08-06
Phase: 3 static extraction implementation
Status: Phase 3 implementation `CLOSED_PASS`; Phase 4 not started.

## Locked Principles

These are not assumptions and must not be weakened during MVP delivery:

- AI/static extractor only creates `candidate`.
- Only reviewer can verify.
- Every `BusinessStatement` requires at least one evidence reference.
- Verified statement changes require revision and lineage.
- No cross-customer semantic learning.
- No best-practice normalization.
- No source upload execution.
- No code translator, BIR runtime, graph database, or microservices in MVP.
- No behavioral equivalence claim.
- Phase 1 must include mandatory Playwright E2E for login -> create project -> project appears in list.

## Baseline Assumptions From Business Analysis

| ID | Assumption | Status |
|---|---|---|
| ASM-001 | Source package is primarily text. | Accepted for MVP |
| ASM-002 | Users have legal rights to upload and analyze source. | Accepted; should be visible in admin/project policy later |
| ASM-003 | At least one reviewer understands code or business context. | Accepted |
| ASM-004 | MVP runs in a controlled environment. | Accepted |
| ASM-005 | Concurrent user count is low. | Accepted |
| ASM-006 | Demo project does not use sensitive production data. | Accepted |
| ASM-007 | One AI provider or mock adapter is sufficient for MVP. | Refined: mock adapter is mandatory; real provider is optional stretch scope |
| ASM-008 | MVP proves workflow, not a complete legacy parser. | Accepted |

## Phase 0 Decisions Locked Before Phase 1

| ID | Decision | Status | Phase 1 impact |
|---|---|---|---|
| DEC-001 | Use Python 3.12 via `py -3.12`, not default Python 3.13, for backend tooling. | Accepted | Backend scaffold must target Python 3.12. |
| DEC-002 | Git was initialized in `D:\BIR` during Phase 0. | Accepted | Per-phase commits are mandatory. |
| DEC-003 | Use Docker Compose as the authoritative local runtime for PostgreSQL and Redis. | Accepted | Phase 1 compose stack must include PostgreSQL 16 and Redis. |
| DEC-004 | Use opaque server-side sessions with HTTP-only cookies, not browser JWT. | Accepted in ADR-002 | Phase 1 auth/session implementation is locked. |
| DEC-005 | Use `SameSite=Lax`, production `Secure=true`, local `Secure=false` allowed, and CSRF tokens for state-changing requests. | Accepted in ADR-002 | Phase 1 security tests must cover cookie flags and CSRF. |
| DEC-006 | Store sessions server-side in PostgreSQL or Redis and invalidate them server-side on logout. | Accepted in ADR-002 | Phase 1 must include session storage and invalidation tests. |
| DEC-007 | Development seed user exists only when `APP_ENV=development`; seed password comes from environment. | Accepted in ADR-002 | No hardcoded seed password may be committed. |
| DEC-008 | Rate limit login by IP and account identifier hash. | Accepted in ADR-002 | Phase 1 auth tests must include rate-limit coverage. |
| DEC-009 | Project creation always starts in `draft`; allowed transitions are locked in `implementation_plan.md`. | Accepted | Phase 1 project CRUD must use domain/application transition rules. |
| DEC-010 | `PATCH /projects/{id}` cannot change `status` arbitrarily. | Accepted | Status changes must use explicit service commands. |
| DEC-011 | Archive is irreversible in MVP; archived projects are read-only. | Accepted | No unarchive flow in Phase 1. |
| DEC-012 | Uploading new source after `export_ready` moves the project to `ingesting`, then `ready_for_analysis` after ingestion. | Accepted | Prior exports remain immutable snapshots; current readiness is revoked. |
| DEC-013 | MVP UI is English-first; localization is outside Phase 1. | Accepted | Phase 1 UI copy can be English. |
| DEC-014 | Physical project deletion is outside MVP; no delete project API or UI. | Accepted | Phase 1 implements archive only. |
| DEC-015 | Mock AI adapter is mandatory; real provider is optional stretch scope after mock tests pass. | Accepted | Phase 5 can pass with mock adapter if boundary tests pass. |
| DEC-016 | Python and Node dependencies must be locked; linting/type checks are CI gates once tooling exists; committed/applied migrations are not edited in place. | Accepted | Phase 1 must commit lock files and migration discipline. |

## Phase 2 Decisions Locked During Implementation

| ID | Decision | Status | Impact |
|---|---|---|---|
| DEC-017 | Source artifact storage paths are generated from project id and artifact id, not user filenames. | Accepted | Prevents filename-driven path placement and supports immutable artifact storage. |
| DEC-018 | Phase 2 text allowlist is `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`. | Accepted | Unsupported files produce ingestion warnings and are not stored as source artifacts. |
| DEC-019 | Default ingestion limits are `MAX_UPLOAD_BYTES=20971520`, `MAX_ZIP_ENTRIES=1000`, `MAX_ZIP_PATH_LENGTH=240`, `MAX_ZIP_UNCOMPRESSED_BYTES=104857600`, and `MAX_ZIP_COMPRESSION_RATIO=100`. | Accepted | Limits are configurable through environment variables and tested with lower limits in integration tests. |
| DEC-020 | Content sniffing rejects NUL bytes and high-control-byte samples as binary-looking content before text decoding. | Accepted | Binary-looking allowed-extension files produce warnings and are not stored as source artifacts. |
| DEC-021 | ZIP validation rejects path traversal, absolute paths, Windows-drive-style paths, symlinks, nested archive extensions, duplicate normalized paths, encrypted entries, and decompression limit violations before any artifact write. | Accepted | Unsafe ZIPs leave no source artifacts and restore project state to the previous stable state. |
| DEC-022 | Source viewer receives API-escaped source lines and renders them as escaped HTML with line numbers. | Accepted | Uploaded source remains untrusted and cannot become executable UI markup. |
| DEC-023 | Upload reads are bounded by chunk and stop when `MAX_UPLOAD_BYTES` is exceeded. | Accepted | Oversized uploads do not proceed into parsing/storage and receive failure audit. |
| DEC-024 | Artifact content is integrity-checked by SHA-256 before source viewer decode. | Accepted | Tampered artifact files are rejected and audited as `ARTIFACT_INTEGRITY_MISMATCH`. |
| DEC-025 | Encoding detection checks `cp932` and `shift_jis` before `cp1252` and `latin-1`; Latin-1 fallback is low confidence. | Accepted | Legacy Japanese source is identified more accurately, and Latin-1 fallback creates a warning. |
| DEC-026 | MVP default upload limit remains 20 MB; `MAX_UPLOAD_BYTES` stays environment-configurable; upload 100 MB plus progress UI is deferred to Phase 7 or post-MVP. | Accepted by Product Owner on 2026-08-06 | Resolves OPEN-002 and removes the Phase 2 documentation blocker. |

## Phase 3 Decisions Locked During Design And Implementation

The Phase 3 design received Architect `CLOSED_PASS_DESIGN` on 2026-08-06. Implementation was authorized on branch `phase-3-static-extraction`.

| ID | Decision | Status | Impact |
|---|---|---|---|
| DEC-027 | `docs/implementation_contract/phase3_static_extraction_contract.md` is the Phase 3 design baseline. | Accepted | Implementation must follow this contract; later changes require gate review. |
| DEC-028 | Add Alembic migration `0003_phase3_static_extraction` for analyzer versions, analysis jobs, chunks, candidates, evidence, gaps, and unresolved questions. | Implemented | Existing migrations remain immutable. |
| DEC-029 | Analysis failure/cancel is `analyzing -> previous_project_status`, with `previous_project_status` stored on `AnalysisJob`, default `ready_for_analysis`, and audit `ANALYSIS_FAILED_OR_CANCELLED`. | Implemented | ADR-003 and `project_state.py` updated. |
| DEC-030 | Use `request_fingerprint` shared across retries plus per-attempt `attempt_no`; unique `(project_id, request_fingerprint, attempt_no)`. | Implemented | Avoids retry collision with idempotency uniqueness. |
| DEC-031 | MVP allows only one active analysis job per project; active means `queued` or `running`. | Implemented | Prevents project status races and requires HTTP `409` on concurrent job creation. |
| DEC-032 | Server owns analyzer identity, version, pattern set hash, supported config keys, config bounds, and canonical config hash. | Implemented | Clients submit only artifact IDs and allowlisted configuration. |
| DEC-033 | Candidate, evidence, gap, and question rows include `analysis_job_id`; worker-created rows use `created_by_kind=system`. | Implemented | Strengthens provenance beyond nullable `created_by`. |
| DEC-034 | Evidence has a DB check constraint requiring exactly one target FK among statement, gap, and unresolved question. | Implemented | Moves target integrity into the database plus application validation. |
| DEC-035 | Keep `source_artifacts.candidate_count` as a transactionally maintained cache; do not persist `business_statements.evidence_count` in Phase 3. | Implemented | Statement APIs compute evidence count by query. |
| DEC-036 | Candidate identity is provenance-based: pattern ID, artifact hash, evidence ranges, structured expression, scope, analyzer version, and config hash; statement text is not a primary identity component. | Implemented | Prevents wording/template changes from driving identity. |
| DEC-037 | Static extractor is insert-only for `BusinessStatement`, `Evidence`, `AnalysisGap`, and `UnresolvedQuestion`; no candidate `UPDATE`, `UPSERT`, merge, or lineage mutation is allowed in Phase 3. | Implemented | Cross-run candidate lineage is deferred to Phase 4 review/revision semantics. |
| DEC-038 | From Phase 4 onward, delivery is split into independently reviewed Epics instead of one large Phase -> Code -> Review cycle. | Accepted by Architect on 2026-08-06 | Phase 4 starts with Epic 4.1 Review Domain and does not close until all required Phase 4 Epics pass review. |

## Requirement Conflicts Or Tensions

| ID | Issue | Locked Phase 0 resolution | Blocking current phase? |
|---|---|---|---|
| CLAR-001 | SRS required evidence for candidate statements while BA allowed candidate without evidence as `unknown_behavior`. | Every `BusinessStatement` must have at least one evidence reference. If the analyst knows there is an unresolved area but cannot create a valid evidence-backed statement, use `AnalysisGap` or `UnresolvedQuestion`. `unknown_behavior`, if used as a statement type, must still link to evidence showing unresolved behavior. | No |
| CLAR-002 | Technical review and business review were described, but MVP has one `reviewer` role. | MVP uses one `reviewer` role. A single valid reviewer decision can verify. Every decision must include `review_context`: `technical`, `business`, or `combined`. Review decisions should support `confidence_source` when available. Export includes review context and should include confidence source. No two-stage approval gate in MVP. | No |
| CLAR-003 | `merge_candidates` could conflict with no auto-merge and contradiction preservation. | Manual merge creates a new candidate or statement revision. Source candidates are not deleted; they become `superseded`; lineage and evidence links are preserved. Merge is blocked when unresolved scope conflict remains. | No |
| CLAR-004 | SRS says one behavioral test per verified rule, while BA export readiness allows documented exceptions. | Export readiness requires each verified rule to have either a linked behavioral test or documented exception/warning. | No |
| CLAR-005 | Secure session mechanism was undecided. | Resolved by ADR-002: opaque server-side session, HTTP-only cookie, CSRF, timeouts, server-side invalidation. | No |
| CLAR-006 | Demo/capacity targets differ between 20-file ZIP, 100 files, and 100 MB upload. | Treat 20-file ZIP as demo acceptance; keep MVP default upload limit at 20 MB; defer 100 MB upload plus progress to Phase 7/post-MVP per DEC-026. | No |
| CLAR-007 | Physical deletion was mentioned but conflicts with immutable artifacts and audit expectations. | Physical deletion is deferred outside MVP. No delete project API or UI. Archive only. | No |
| CLAR-008 | Real AI provider scope could expand unexpectedly. | Mock adapter is mandatory. Real provider is optional stretch scope; Phase 5 can pass with mock adapter if boundaries are proven. | No |
| CLAR-009 | Project status transitions and rollback rules were incomplete. | Project state machine is locked in `implementation_plan.md`, including allowed transitions, actors, preconditions, invalid transitions, archive behavior, and source upload after `export_ready`. | No |
| CLAR-010 | `mark_obsolete_candidate` did not match the statement state machine. | Do not add `obsolete` status in MVP. Store structured `historical_validity` metadata tied to a review decision. Do not delete historically valid statements. | No |

## Evidence, Unknown Behavior, Gaps, and Questions

Official Phase 0 rule:

- A `BusinessStatement` always requires at least one evidence reference.
- `unknown_behavior` is allowed only when it links to evidence showing a behavior exists but is not yet understood.
- Examples of valid evidence for `unknown_behavior`: unresolved dynamic call, procedure without source, unclear status code, external program invocation, unreadable binary dependency.
- If there is no evidence-backed statement to make, record an `AnalysisGap` or `UnresolvedQuestion`.
- `AnalysisGap` and `UnresolvedQuestion` are not verified business knowledge and cannot be exported as verified statements.

## Review, Merge, and Obsolete Representation

Review:

- One `reviewer` role is used in MVP.
- `review_context` is required with values `technical`, `business`, or `combined`.
- `confidence_source` should be stored as a list when available, with values such as `source_code`, `sme_interview`, `operating_manual`, `database`, or `runtime_log`.
- One valid reviewer decision is sufficient to verify in MVP.
- Export must include the review context.
- Export should include `confidence_source` when review decisions provide it.

Merge:

- Candidate A plus Candidate B produces new Candidate/Revision C.
- A and B are not deleted.
- A and B become `superseded`.
- C stores lineage to A and B.
- Evidence from A and B is retained as evidence links.
- Merge is blocked when unresolved scope conflict exists.

Obsolete/historic validity metadata:

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

This is metadata, not a new statement state.

## Requirements That Are Not Yet Fully Testable

| ID | Requirement | Testability gap | Proposed action | Blocking current phase? |
|---|---|---|---|---|
| NT-001 | No best-practice normalization. | Hard to prove absence globally. | Add negative tests for known auto-normalization paths and keep review checklist/manual audit. | No |
| NT-002 | Candidate statement is readable. | Readability is subjective. | Use schema validation plus reviewer feedback; avoid treating it as automated pass/fail. | No |
| NT-003 | Evidence range precision. | Needs labeled benchmark for objective precision. | Demo fixture should include expected line ranges. | No |
| NT-004 | Reviewer rubber-stamping mitigation. | Sampling audit is described as later mitigation, not MVP feature. | Require reason for review decisions in MVP; defer sampling audit. | No |
| NT-005 | No source leakage in production logs. | Requires log policy and environment-mode tests. | Add production-mode log redaction tests in Phase 5. | No |
| NT-006 | 100% understood / completeness is explicitly not a goal. | Users may infer completeness from dashboard. | UI copy must label dashboard as evidence coverage only. | No |
| NT-007 | Business SME understands statement. | Requires user research, not just automated tests. | Track under product validation plan H2. | No |
| NT-008 | Traceable export is useful for modernization architects. | Requires stakeholder validation. | Track under product validation plan H4. | No |

## Security Gates

| ID | Gap or gate | Decision/status | Blocking current phase? |
|---|---|---|---|
| SEC-GATE-001 | CSRF strategy if cookie sessions are used. | Resolved in ADR-002: CSRF token required for state-changing requests. | No |
| SEC-GATE-002 | Session cookie flags and invalidation behavior. | Resolved in ADR-002: HTTP-only, `SameSite=Lax`, environment-specific `Secure`, server-side invalidation. | No |
| SEC-GATE-003 | Password policy and seed-user handling. | Resolved in ADR-002: secure hash, generic errors, dev seed only under `APP_ENV=development`, password from environment. | No |
| SEC-GATE-004 | Rate-limit algorithm and storage. | Resolved in ADR-002: login rate limit by IP and account identifier hash; AI rate limiting in Phase 5. | No |
| SEC-GATE-005 | ZIP symlink, nested ZIP, path length, Unicode normalization, and entry-count limits. | Resolved in Phase 2 and covered by integration tests. | No |
| SEC-GATE-006 | Content sniffing vs extension-only allowlist. | Resolved in Phase 2: extension allowlist plus binary-looking content sniffing. | No |
| SEC-GATE-007 | Export authorization and exported file retention. | Decide in Phase 7 export implementation. | No |
| SEC-GATE-008 | Audit log tamper resistance/retention. | Phase 1 records append-only audit events; stronger tamper resistance/retention is Phase 7/post-MVP. | No |
| SEC-GATE-009 | AI prompt-injection handling. | Phase 5 AI adapter must treat source as hostile and instruction-isolated. | No |
| SEC-GATE-010 | CORS allowed origins. | Phase 1 must restrict origins through environment config. | No |

## Scope Drift Risks

| ID | Risk | Boundary |
|---|---|---|
| SCOPE-001 | Turning extraction into a full COBOL compiler/parser. | MVP uses deterministic patterns and simple chunking. |
| SCOPE-002 | Building code translation or target system generation. | Explicitly outside MVP. |
| SCOPE-003 | Introducing graph database for lineage/conflict. | Use relational tables and JSON fields for MVP. |
| SCOPE-004 | Splitting into microservices too early. | Use modular monolith with clear internal modules. |
| SCOPE-005 | Building industry ontology or cross-customer templates. | Project-scoped glossary only. |
| SCOPE-006 | Treating AI confidence as business truth. | Confidence is extractor confidence only. |
| SCOPE-007 | Adding production mainframe trace capture. | Manual/simulated tests only in MVP. |
| SCOPE-008 | Trying to prove behavioral equivalence. | Export behavioral tests, no equivalence claim. |
| SCOPE-009 | Building enterprise SSO/multi-tenant SaaS governance. | Local auth and simple roles only. |
| SCOPE-010 | Making dashboard imply complete business coverage. | Dashboard is evidence coverage, not absolute completeness. |

## Remaining Open Assumptions

| ID | Assumption | Phase affected | Status / blocking impact |
|---|---|---|---|
| OPEN-001 | Exact ZIP scanner numeric limits for entry count, path length, nesting, and decompression ratio. | Phase 2 | Resolved in DEC-019. |
| OPEN-002 | Product decision for SRS `Upload 100 MB có progress`. | Phase 2/7 | Resolved in DEC-026: MVP default is 20 MB, the limit remains environment-configurable, and 100 MB/progress is deferred to Phase 7 or post-MVP. |
| OPEN-003 | Export retention period and cleanup policy. | Phase 7 | No |
| OPEN-004 | Stakeholder validation of statement readability and export usefulness. | Product validation, post-slice | No |

Phase 3 implementation blocking assumptions: none. Phase 3 closed as `CLOSED_PASS`.

Phase 4 implementation must follow the Epic delivery model in DEC-038. No Phase 4 code should begin until the intended Epic scope is explicit.

## Assumption Update Rule

Any new assumption discovered during implementation must be added here with:

- Stable ID.
- Source/context.
- Impact.
- Whether it is accepted, needs user decision, or is deferred.
- Whether it blocks the current phase.
