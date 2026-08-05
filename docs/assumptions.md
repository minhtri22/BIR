# Assumptions, Open Questions, and MVP Risk Register

Date: 2026-08-05
Phase: 0 revision baseline
Status: Phase 0 revision complete; Phase 1 remains blocked until user approval.

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

## Requirement Conflicts Or Tensions

| ID | Issue | Locked Phase 0 resolution | Blocking Phase 1? |
|---|---|---|---|
| CLAR-001 | SRS required evidence for candidate statements while BA allowed candidate without evidence as `unknown_behavior`. | Every `BusinessStatement` must have at least one evidence reference. If the analyst knows there is an unresolved area but cannot create a valid evidence-backed statement, use `AnalysisGap` or `UnresolvedQuestion`. `unknown_behavior`, if used as a statement type, must still link to evidence showing unresolved behavior. | No |
| CLAR-002 | Technical review and business review were described, but MVP has one `reviewer` role. | MVP uses one `reviewer` role. A single valid reviewer decision can verify. Every decision must include `review_context`: `technical`, `business`, or `combined`. Export includes review context. No two-stage approval gate in MVP. | No |
| CLAR-003 | `merge_candidates` could conflict with no auto-merge and contradiction preservation. | Manual merge creates a new candidate or statement revision. Source candidates are not deleted; they become `superseded`; lineage and evidence links are preserved. Merge is blocked when unresolved scope conflict remains. | No |
| CLAR-004 | SRS says one behavioral test per verified rule, while BA export readiness allows documented exceptions. | Export readiness requires each verified rule to have either a linked behavioral test or documented exception/warning. | No |
| CLAR-005 | Secure session mechanism was undecided. | Resolved by ADR-002: opaque server-side session, HTTP-only cookie, CSRF, timeouts, server-side invalidation. | No |
| CLAR-006 | Demo/capacity targets differ between 20-file ZIP, 100 files, and 100 MB upload. | Treat 20-file ZIP as demo acceptance; 100 text files and 100 MB upload as capacity/performance tests. | No |
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
- One valid reviewer decision is sufficient to verify in MVP.
- Export must include the review context.

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

| ID | Requirement | Testability gap | Proposed action | Blocking Phase 1? |
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

| ID | Gap or gate | Decision/status | Blocking Phase 1? |
|---|---|---|---|
| SEC-GATE-001 | CSRF strategy if cookie sessions are used. | Resolved in ADR-002: CSRF token required for state-changing requests. | No |
| SEC-GATE-002 | Session cookie flags and invalidation behavior. | Resolved in ADR-002: HTTP-only, `SameSite=Lax`, environment-specific `Secure`, server-side invalidation. | No |
| SEC-GATE-003 | Password policy and seed-user handling. | Resolved in ADR-002: secure hash, generic errors, dev seed only under `APP_ENV=development`, password from environment. | No |
| SEC-GATE-004 | Rate-limit algorithm and storage. | Resolved in ADR-002: login rate limit by IP and account identifier hash; AI rate limiting in Phase 5. | No |
| SEC-GATE-005 | ZIP symlink, nested ZIP, path length, Unicode normalization, and entry-count limits. | Locked as Phase 2 ingestion requirements. | No |
| SEC-GATE-006 | Content sniffing vs extension-only allowlist. | Decide exact sniffing implementation in Phase 2; not needed for Phase 1 foundation. | No |
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

| ID | Assumption | Phase affected | Blocking Phase 1? |
|---|---|---|---|
| OPEN-001 | Exact ZIP scanner numeric limits for entry count, path length, nesting, and decompression ratio. | Phase 2 | No |
| OPEN-002 | Exact upload progress implementation details for 100 MB local upload. | Phase 2/7 | No |
| OPEN-003 | Export retention period and cleanup policy. | Phase 7 | No |
| OPEN-004 | Stakeholder validation of statement readability and export usefulness. | Product validation, post-slice | No |

Phase 1 blocking assumptions: none.

## Assumption Update Rule

Any new assumption discovered during implementation must be added here with:

- Stable ID.
- Source/context.
- Impact.
- Whether it is accepted, needs user decision, or is deferred.
- Whether it blocks the current phase.
