# CODEX HANDOFF — BUSINESS FORENSICS MVP

## Nhiệm vụ
Xây dựng MVP dựa trên hai tài liệu bắt buộc:
1. `01_business_forensics_mvp_requirements.md`
2. `02_business_forensics_mvp_business_analysis.md`

Không mở rộng thành code translator, BIR runtime, industry ontology hoặc modernization platform hoàn chỉnh.

## Product intent
Business Forensics Platform giúp tái dựng hành vi nghiệp vụ của một hệ thống legacy cụ thể dựa trên bằng chứng.

```text
Legacy source
→ inventory
→ candidate statements
→ evidence/provenance
→ uncertainty/conflict
→ human review
→ verified statements
→ behavioral tests
→ traceable export
```

## Nguyên tắc bắt buộc
- AI/static extractor chỉ tạo `candidate`.
- Chỉ reviewer mới được chuyển sang `verified`.
- Verified statement phải có evidence hợp lệ.
- Không học chéo nghiệp vụ giữa khách hàng.
- Không áp đặt best practice ngành.
- Không auto-merge statement khác scope.
- Không bỏ exception, conflict hoặc uncertainty.
- Verified statement sửa bằng revision, không sửa trực tiếp.
- Không execute source upload.
- Không hardcode một AI provider.
- Không dùng microservices hoặc graph database trong MVP.
- Không dịch legacy code sang Java/.NET.
- Không tuyên bố behavioral equivalence.
- Mọi assumption mới ghi vào `docs/assumptions.md`.

## Stack mặc định
Backend:
- Python 3.12, FastAPI, Pydantic v2
- SQLAlchemy 2, Alembic, PostgreSQL 16
- Dramatiq + Redis

Frontend:
- React, TypeScript strict, Vite

Testing:
- pytest, integration tests, Playwright

Packaging:
- Docker Compose
- Local storage abstraction, có interface mở rộng S3-compatible

## Kiến trúc
Dùng modular monolith:

```text
Web UI
→ REST API
→ Application Services
→ Domain Layer
→ PostgreSQL / file storage / worker / AI adapters
```

Business state transition không đặt trong controller.

## Thứ tự triển khai
### Phase 0 — Audit và plan
Trước khi code:
- Đọc ba tài liệu.
- Audit repo.
- Tạo:
  - `docs/implementation_plan.md`
  - `docs/requirements_traceability.md`
  - `docs/assumptions.md`
  - `docs/architecture_decisions/`
- Lập ma trận requirement → module → test.
- Phản biện requirement mâu thuẫn, chưa testable, security gate thiếu và phạm vi dễ trượt.

### Phase 1 — Foundation
- Docker Compose
- Backend/frontend/worker
- DB migrations
- Local auth và RBAC
- Project CRUD
- Audit foundation
- Health endpoint
- CI test

### Phase 2 — Secure ingestion
- ZIP upload
- Path traversal và ZIP bomb protection
- Immutable artifacts
- SHA-256, encoding, inventory
- Source viewer
- Audit

### Phase 3 — Static extraction
- Chunking
- Deterministic patterns
- Candidate + evidence ranges
- Idempotency theo artifact hash + analyzer version

### Phase 4 — Review workflow
- State machine
- Review decisions
- Evidence validation
- Revision
- Conflict
- RBAC
- Audit

### Phase 5 — AI adapter
- Provider-independent interface
- Mock adapter trước
- Một provider thật sau khi mock tests pass
- Structured output validation
- AI không thể tạo verified state
- Async jobs

### Phase 6 — Conflict, glossary, tests
- Glossary
- Conflict workspace
- Behavioral tests
- Manual execution result
- Traceability

### Phase 7 — Dashboard và export
- Coverage dashboard
- Versioned JSON export ZIP
- E2E happy path
- Demo seed package

## First vertical slice
Hoàn thành trước:

```text
Login
→ Create project
→ Upload one source file
→ Generate one deterministic candidate
→ Show evidence
→ Reviewer verifies
→ Create behavioral test
→ Export JSON
```

Phải có migration, API, UI, authorization, audit, unit, integration và E2E test.

## State machine
```text
candidate
→ under_review
→ verified
→ rejected
→ needs_evidence
→ conflicted
→ superseded
```

Rules:
- AI/static chỉ tạo candidate.
- Verified cần reviewer và evidence.
- Verified thay đổi phải tạo revision.
- Superseded phải có lineage.
- Transition quan trọng phải có ReviewDecision và AuditEvent.

## AI adapter boundary
AI adapter không được:
- Truy cập DB trực tiếp
- Ghi statement
- Thay đổi status
- Tạo review decision
- Dùng knowledge khách hàng khác như fact
- Log source đầy đủ trong production

Backend phải validate schema, evidence bounds, confidence, ép status về candidate và persist qua application service.

## Security gates
Phải test:
- ZIP path traversal
- ZIP bomb
- Binary unsupported
- Filename/storage isolation
- HTML escaping
- Upload limit
- No source execution
- Password hashing
- Viewer cannot review
- Backend RBAC
- Login rate limit
- Secure session

## Test bắt buộc
1. ZIP path traversal
2. Duplicate analysis idempotency
3. AI invalid output
4. AI attempts `verified`
5. Human verify with evidence
6. Verify without evidence blocked
7. Verified direct edit blocked
8. Conflict preservation
9. Export reproducibility
10. Viewer review forbidden
11. Artifact hash preserved
12. Evidence line range validation
13. Revision lineage
14. Audit event on review
15. No source execution

## Demo fixture
Project: `Legacy Purchase Approval`

Files:
- `PURCHASE01.cbl`
- `APPROVAL.cbl`
- `LIMITS.cpy`
- `PURCHASE_SCHEMA.sql`
- `operating_notes.md`

Behaviors:
- Manager approval below threshold
- Director approval above threshold
- Emergency override
- End-of-month variation
- One ambiguous/conflicting old rule
- Status update SQL
- Notification call

## Sau mỗi phase
Cập nhật:
- `docs/progress.md`
- `docs/requirements_traceability.md`
- `docs/assumptions.md`
- Test report
- Known limitations
- Git status

Mỗi phase commit riêng. Không commit secret, `.env`, source upload hoặc AI key.

## Lệnh bắt đầu cho Codex
1. Đọc ba file đặc tả.
2. Audit repository và môi trường.
3. Không code ngay.
4. Tạo implementation plan, traceability và assumptions.
5. Phản biện requirement và security.
6. Triển khai Phase 0 rồi Phase 1.
7. Chạy test thực tế.
8. Báo cáo file thay đổi, test evidence, limitations và next phase.
