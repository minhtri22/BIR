# Assumptions, Open Questions, and MVP Risk Register

Date: 2026-08-05  
Phase: 0 baseline

## Locked Principles

These are not assumptions and should not be weakened during MVP delivery:

- AI/static extractor only creates `candidate`.
- Only reviewer can verify.
- Verified statement requires valid evidence.
- Verified statement changes require revision and lineage.
- No cross-customer semantic learning.
- No best-practice normalization.
- No source upload execution.
- No code translator, BIR runtime, graph database, or microservices in MVP.
- No behavioral equivalence claim.

## Baseline Assumptions From Business Analysis

| ID | Assumption | Status |
|---|---|---|
| ASM-001 | Source package is primarily text. | Accepted for MVP |
| ASM-002 | Users have legal rights to upload and analyze source. | Accepted, should be visible in admin/project policy later |
| ASM-003 | At least one reviewer understands code or business context. | Accepted |
| ASM-004 | MVP runs in a controlled environment. | Accepted |
| ASM-005 | Concurrent user count is low. | Accepted |
| ASM-006 | Demo project does not use sensitive production data. | Accepted |
| ASM-007 | One AI provider or mock adapter is sufficient for MVP. | Accepted |
| ASM-008 | MVP proves workflow, not a complete legacy parser. | Accepted |

## New Phase 0 Assumptions To Lock

| ID | Assumption | Reason | Decision needed |
|---|---|---|---|
| ASM-009 | Use Python 3.12 via `py -3.12`, not the default Python 3.13, for backend tooling. | Handoff requires Python 3.12 and local 3.12 is available. | Lock in Phase 1 tooling. |
| ASM-010 | Initialize Git in `D:\BIR` during Phase 0. | Workspace is not currently a Git repository, but phase commits are required. | Proceed unless user prefers external repo initialization. |
| ASM-011 | Use Docker Compose as the authoritative local runtime for PostgreSQL and Redis. | Docker and Compose are installed and required by SRS. | Lock in Phase 1. |
| ASM-012 | Use HTTP-only secure session cookie for MVP auth rather than bearer JWT. | SRS allows cookie or JWT; cookie reduces token exposure in browser UI. | Confirm before hardening session behavior. |
| ASM-013 | Seed local admin/reviewer users through controlled dev seed, not committed secrets. | MVP needs login before user-management UI exists. | Define seed mechanism in Phase 1. |
| ASM-014 | Store uploaded artifacts under generated IDs/content-addressed paths, never raw user filenames. | Required for storage isolation and path safety. | Lock in Phase 2. |
| ASM-015 | Unsupported/binary files produce ingest warnings and no artifact content view. | SRS says skip unsupported binary with warning. | Define exact API status codes in Phase 2. |
| ASM-016 | Real AI provider implementation is deferred until mock adapter tests pass. | Handoff requires mock first; SRS allows mock or provider. | Lock Phase 5 entry criteria. |
| ASM-017 | UI text can be English-first with domain terms, unless Vietnamese UI is requested before Phase 1. | SRS allows Vietnamese/English basic but does not define copy requirements. | Needs product decision. |
| ASM-018 | Physical project deletion is not exposed in MVP UI. | SRS says admin deletion mechanism exists but not in UI until controlled enough. | Define whether backend-only admin endpoint is needed. |

## Requirement Conflicts Or Tensions

| ID | Issue | Why it matters | Proposed Phase 0 position |
|---|---|---|---|
| CLAR-001 | SRS says every candidate statement must link to at least one evidence range, while BA says candidate without evidence can be saved as `unknown_behavior` until evidence or approved justification exists. | A universal evidence requirement conflicts with an unknown-behavior workflow. | Treat normal extracted statements as requiring evidence. Allow `unknown_behavior` only as an uncertainty record that cannot be verified without evidence or explicit approved justification. |
| CLAR-002 | Review workflow mentions Technical review and Business review, but MVP role model has a single `reviewer` role and a single statement state machine. | Verification authority and audit semantics could become ambiguous. | Use one `reviewer` role in Phase 1/4, but include `reviewer_type` or decision metadata for technical/business review context. |
| CLAR-003 | `merge_candidates` is allowed in UC-07, while no auto-merge and preserve contradiction are mandatory principles. | Manual merge can accidentally erase scope/evidence differences. | Only manual reviewer/analyst-assisted merge with explicit lineage and no cross-scope auto-merge; keep conflicts first-class. |
| CLAR-004 | SRS says one behavioral test per verified rule, while BA export readiness allows documented exceptions for important rules. | Export readiness cannot be deterministic without an exception policy. | Require verified rule coverage to be either linked test or documented exception/warning. |
| CLAR-005 | "Secure session" is required but cookie vs JWT is undecided. | CSRF, cookie flags, invalidation, and tests differ by mechanism. | Use HTTP-only cookie unless user redirects. |
| CLAR-006 | Performance target says upload 100 MB with progress, while initial acceptance says ZIP with at least 20 files and quantitative goal says import 100 files. | Phase acceptance could drift between demo and capacity testing. | Treat 20-file ZIP as demo acceptance, 100 text files and 100 MB upload as capacity/performance tests. |
| CLAR-007 | Project physical deletion is listed as a security requirement but also outside MVP UI until controlled. | Deletion can conflict with immutable artifacts and audit expectations. | Do not expose in UI. Decide later whether backend/admin CLI deletion is required for MVP acceptance. |
| CLAR-008 | "AI provider thật sau khi mock tests pass" in handoff is stricter than SRS acceptance allowing mock or provider. | Phase 5 scope can expand unexpectedly. | Mock adapter is required; one real provider is optional unless explicitly confirmed as MVP acceptance. |
| CLAR-009 | Project status transitions are listed, but allowed transitions and rollback rules are incomplete. | Controllers might encode inconsistent transitions. | Define state machine in domain layer in Phase 1 before broad project workflows. |
| CLAR-010 | `mark_obsolete_candidate` exists as review action, but state machine does not list `obsolete`. | Status model and action model are not aligned. | Represent obsolete as review metadata/resolution until temporal model is introduced; do not add new status without explicit decision. |

## Requirements That Are Not Yet Fully Testable

| ID | Requirement | Testability gap | Proposed action |
|---|---|---|---|
| NT-001 | "No best-practice normalization." | Hard to prove absence globally. | Add negative tests for known auto-normalization paths and keep review checklist/manual audit. |
| NT-002 | "Candidate statement is readable." | Readability is subjective. | Use schema validation plus reviewer feedback; avoid treating it as automated pass/fail. |
| NT-003 | "Evidence range precision." | Needs labeled benchmark for objective precision. | Demo fixture should include expected line ranges. |
| NT-004 | "Reviewer rubber-stamping mitigation." | Sampling audit is described as later mitigation, not MVP feature. | Require reason for review decisions in MVP; defer sampling audit. |
| NT-005 | "No source leakage in production logs." | Requires log policy and environment-mode tests. | Add production-mode log redaction tests in Phase 5. |
| NT-006 | "100% understood / completeness" is explicitly not a goal. | Users may still infer completeness from dashboard. | UI copy must label dashboard as evidence coverage only. |
| NT-007 | "Business SME understands statement." | Requires user research, not just automated tests. | Track under product validation plan H2. |
| NT-008 | "Traceable export is useful for modernization architects." | Requires stakeholder validation. | Track under product validation plan H4. |

## Missing Or Underspecified Security Gates

| ID | Gap | Risk | Phase to decide |
|---|---|---|---|
| SEC-GAP-001 | CSRF strategy if cookie sessions are used. | Authenticated state-changing requests may be vulnerable. | Phase 1 |
| SEC-GAP-002 | Session cookie flags and invalidation behavior not specified. | Session theft or stale sessions. | Phase 1 |
| SEC-GAP-003 | Password policy, lockout, and seed-user handling not specified. | Weak local credentials or leaked dev accounts. | Phase 1 |
| SEC-GAP-004 | Rate-limit algorithm and storage not specified. | Inconsistent login/AI throttling. | Phase 1/5 |
| SEC-GAP-005 | ZIP symlink, nested ZIP, path length, Unicode normalization, and entry-count limits not specified. | Bypass of path/storage restrictions. | Phase 2 |
| SEC-GAP-006 | Content sniffing vs extension-only allowlist not specified. | Binary/polyglot content may be treated as safe text. | Phase 2 |
| SEC-GAP-007 | Export authorization and exported file retention not specified. | Unauthorized or stale export downloads. | Phase 7 |
| SEC-GAP-008 | Audit log tamper resistance/retention not specified. | Audit value may be weakened. | Phase 1/7 |
| SEC-GAP-009 | AI prompt-injection handling not specified. | Source content may influence extraction instructions. | Phase 5 |
| SEC-GAP-010 | CORS allowed origins not specified. | Overly broad browser access in local/prod mode. | Phase 1 |

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

## Assumption Update Rule

Any new assumption discovered during implementation must be added here with:

- Stable ID.
- Source/context.
- Impact.
- Whether it is accepted, needs user decision, or is deferred.

