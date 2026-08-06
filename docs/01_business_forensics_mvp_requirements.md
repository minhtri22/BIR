# BUSINESS FORENSICS PLATFORM
## Software Requirements Specification for MVP
**Document ID:** BFP-SRS-001  
**Version:** 0.1  
**Status:** Draft for MVP implementation  
**Language:** Vietnamese  
**Primary purpose:** Làm đầu vào trực tiếp cho AI coder xây dựng MVP có thể chạy và kiểm thử.

---

# 1. Tóm tắt sản phẩm

Business Forensics Platform là nền tảng hỗ trợ tái dựng cách một hệ thống nghiệp vụ cũ đang thực sự vận hành dựa trên bằng chứng, thay vì suy diễn theo best practice hoặc ontology ngành.

MVP tập trung vào một bài toán hẹp:

> Nhập một gói mã nguồn legacy dạng text, cho phép hệ thống trích xuất các phát biểu nghiệp vụ ứng viên, gắn bằng chứng nguồn, quản lý bất định, review bởi con người, và tạo tập kiểm thử hành vi để so sánh hệ thống cũ với cách diễn giải đã được xác nhận.

MVP không tự động chuyển đổi toàn bộ hệ thống sang công nghệ mới. Nó tạo ra lớp tri thức có thể kiểm chứng để phục vụ các dự án modernization về sau.

---

# 2. Vấn đề cần giải quyết

Các hệ thống legacy thường chứa nghiệp vụ đã tích lũy nhiều năm nhưng:

- Tài liệu không đầy đủ hoặc lỗi thời.
- Người viết hệ thống đã nghỉ việc.
- Code chứa nhiều rule, override và ngoại lệ khó nhận biết.
- Cùng một khái niệm có thể được triển khai tại nhiều module.
- Không thể xác nhận việc chuyển đổi công nghệ có giữ nguyên hành vi cũ hay không.
- Công cụ phân tích hiện tại chủ yếu tạo call graph, dependency graph hoặc dịch code, nhưng không biến kết quả thành tri thức nghiệp vụ có provenance và review state.
- AI có nguy cơ tự hợp lý hóa, chuẩn hóa hoặc bỏ qua ngoại lệ hiếm.

---

# 3. Mục tiêu MVP

MVP phải chứng minh được chuỗi giá trị sau:

```text
Legacy source package
    ↓
Source inventory
    ↓
Candidate business statements
    ↓
Evidence links and confidence
    ↓
Human review
    ↓
Verified business statements
    ↓
Behavioral test cases
    ↓
Traceable export
```

Mục tiêu định lượng ban đầu:

1. Import được tối thiểu 100 tệp text trong một project.
2. Hỗ trợ các phần mở rộng `.cbl`, `.cob`, `.cpy`, `.sql`, `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`.
3. Mỗi candidate statement phải liên kết được với ít nhất một đoạn bằng chứng.
4. Không statement nào được chuyển thành `verified` nếu chưa có hành động xác nhận của reviewer.
5. Có thể truy ngược từ statement đến file và dòng nguồn.
6. Có thể xuất project thành JSON package độc lập với model AI.
7. Có thể tạo tối thiểu một behavioral test case cho mỗi rule đã xác nhận.
8. Có audit log cho mọi thay đổi trạng thái quan trọng.

---

# 4. Ngoài phạm vi MVP

MVP không bao gồm:

- Tự động dịch COBOL sang Java, .NET hoặc ngôn ngữ khác.
- Compiler đầy đủ cho COBOL, RPG, PL/I hoặc Oracle Forms.
- Runtime production chạy toàn bộ BIR.
- Tự động khẳng định behavioral equivalence.
- Học chéo nội dung nghiệp vụ giữa các khách hàng.
- Tự động chuẩn hóa theo ontology ngành.
- Tự động sửa hoặc tối ưu nghiệp vụ.
- Kết nối trực tiếp mainframe production.
- Thu thập trace production theo thời gian thực.
- Multi-tenant SaaS production-grade.
- SSO doanh nghiệp, LDAP, SAML.
- Marketplace hoặc extension SDK.
- Full graph database.
- Tự động sinh hệ thống đích hoàn chỉnh.

---

# 5. Persona

## 5.1. Modernization Analyst

Người nhập source package, chạy phân tích, tổ chức candidate, kiểm tra evidence và chuẩn bị hồ sơ review.

Nhu cầu:

- Biết hệ thống có những module gì.
- Tìm candidate rule, state transition và data transformation.
- Gắn evidence chính xác.
- Theo dõi phần nào chưa rõ.
- Không bị AI tự kết luận thay.

## 5.2. Business SME

Chuyên gia nghiệp vụ đã hoặc đang vận hành hệ thống.

Nhu cầu:

- Đọc phát biểu bằng ngôn ngữ nghiệp vụ.
- Xem bằng chứng nguồn.
- Xác nhận, từ chối hoặc yêu cầu bổ sung.
- Ghi chú lý do tồn tại của rule.
- Đánh dấu ngoại lệ và phạm vi áp dụng.

## 5.3. Technical Reviewer

Kỹ sư hiểu code legacy.

Nhu cầu:

- Kiểm tra mapping giữa statement và code.
- Phát hiện evidence thiếu hoặc sai phạm vi.
- Xác định thứ tự thực thi, override và data dependency.
- Chuyển candidate về trạng thái cần phân tích lại.

## 5.4. Project Administrator

Quản lý project, thành viên và export.

Trong MVP, role có thể đơn giản hóa thành:

- `admin`
- `analyst`
- `reviewer`
- `viewer`

---

# 6. Nguyên tắc thiết kế bắt buộc

1. **Evidence before inference:** Không có evidence thì không được tạo verified knowledge.
2. **Human promotion gate:** Chỉ reviewer được promote candidate thành verified.
3. **No silent normalization:** Không tự sửa terminology, workflow hoặc rule theo best practice.
4. **Preserve uncertainty:** Phải biểu diễn rõ unknown, ambiguous, conflict và insufficient evidence.
5. **Preserve exception:** Rule hiếm vẫn là first-class object.
6. **Preserve contradiction:** Không tự hợp nhất hai statement mâu thuẫn.
7. **Provenance everywhere:** Mọi statement, evidence và review decision đều có nguồn gốc.
8. **Tenant-isolated semantics:** Nội dung project không được dùng làm sự thật cho project khác.
9. **AI is replaceable:** Model AI chỉ là adapter; dữ liệu lõi không phụ thuộc provider.
10. **Deterministic state changes:** State transition của review phải được rule engine kiểm soát, không để AI tự thay đổi.

---

# 7. Phạm vi use case MVP

## UC-01 — Tạo project

Actor: Admin hoặc Analyst.

Input:

- Tên project.
- Mô tả.
- Tên hệ thống cũ.
- Ngôn ngữ/source type.
- Organization name.
- Snapshot date.

Output:

- Project ở trạng thái `draft`.
- Project ID duy nhất.
- Audit event `PROJECT_CREATED`.

## UC-02 — Upload source package

Input:

- Một hoặc nhiều file.
- Có thể upload ZIP.

Hệ thống:

- Giải nén an toàn.
- Chặn path traversal.
- Bỏ qua binary không hỗ trợ.
- Tính SHA-256 cho từng file.
- Phát hiện encoding.
- Lưu bản gốc immutable.
- Tạo source inventory.

Output:

- Danh sách source artifact.
- Trạng thái ingest.
- Warning nếu file không đọc được.

## UC-03 — Xem source inventory

Người dùng xem:

- Path.
- Loại file.
- Kích thước.
- Encoding.
- Hash.
- Số dòng.
- Trạng thái phân tích.
- Số candidate liên quan.

Có chức năng tìm kiếm và lọc.

## UC-04 — Chạy static extraction

MVP hỗ trợ hai chế độ:

### Chế độ deterministic

Dùng regex/parser đơn giản để phát hiện:

- IF/ELSE.
- CASE/EVALUATE.
- Assignment.
- SQL SELECT/INSERT/UPDATE/DELETE.
- Procedure/function references.
- Status comparison.
- Numeric threshold.
- Literal codes.
- Comment block.

### Chế độ AI-assisted

Gửi source chunk đã được chuẩn hóa cho AI adapter để đề xuất candidate.

AI chỉ trả về structured proposal theo JSON Schema.

Output:

- Candidate statements.
- Evidence references.
- Confidence.
- Extraction method.
- Warnings.
- Unresolved questions.

## UC-05 — Xem candidate statement

Mỗi candidate có:

- ID.
- Type.
- Title.
- Natural-language statement.
- Structured expression nếu có.
- Scope.
- Confidence.
- Status.
- Evidence count.
- Unresolved items.
- Extraction method.
- Created by.
- Created time.

## UC-06 — Xem evidence

Evidence phải hiển thị:

- File.
- Dòng bắt đầu/kết thúc.
- Source excerpt.
- Hash của artifact.
- Loại evidence.
- Relation với candidate.
- Ghi chú của analyst.

Không được cho phép sửa bản source excerpt gốc.

## UC-07 — Review candidate

Reviewer có thể:

- `confirm`
- `reject`
- `request_more_evidence`
- `mark_conflict`
- `mark_obsolete_candidate`
- `split_candidate`
- `merge_candidates` nhưng phải giữ lineage

Mỗi quyết định phải có:

- Reviewer.
- Timestamp.
- Reason.
- Before state.
- After state.

## UC-08 — Quản lý terminology

Cho phép tạo glossary theo project:

- Term.
- Meaning.
- Scope.
- Source/evidence.
- Status.
- Effective period.
- Synonyms.
- Ambiguities.

Glossary không được tự áp đặt lên candidate chưa review.

## UC-09 — Quản lý conflict

Conflict record liên kết từ hai statement trở lên.

Các loại conflict:

- Logic conflict.
- Scope overlap.
- Temporal conflict.
- Terminology conflict.
- Execution-order ambiguity.
- Evidence conflict.

Conflict không nhất thiết là lỗi. Có thể kết thúc bằng:

- Both valid in different scopes.
- Priority rule identified.
- Effective dates differ.
- One rejected.
- Unresolved.

## UC-10 — Tạo behavioral test case

Từ verified statement, người dùng tạo test case gồm:

- Preconditions.
- Input.
- Expected outcome.
- Scope.
- Linked statements.
- Linked evidence.
- Test status.
- Execution mode.

MVP chỉ cần manual/simulated execution. Không bắt buộc tích hợp hệ thống thật.

## UC-11 — Xuất project package

Export ZIP gồm:

- `project.json`
- `artifacts.json`
- `statements.json`
- `evidence.json`
- `reviews.json`
- `glossary.json`
- `conflicts.json`
- `behavioral_tests.json`
- `audit_log.json`
- `schema_version.json`

Không export secret hoặc credential.

## UC-12 — Dashboard coverage

Hiển thị:

- Số source artifact.
- Số file đã phân tích.
- Số candidate.
- Số verified.
- Số rejected.
- Số cần thêm evidence.
- Số conflict chưa xử lý.
- Số verified statement chưa có test.
- Coverage theo file/module.

Không gọi đây là “độ đầy đủ nghiệp vụ tuyệt đối”. Chỉ là coverage trên bằng chứng đã nhập.

---

# 8. Mô hình trạng thái

## 8.1. Project

```text
draft
→ ingesting
→ ready_for_analysis
→ analyzing
→ review_in_progress
→ export_ready
→ archived
```

Project có thể quay lại `analyzing` khi bổ sung source.

## 8.2. Candidate statement

```text
candidate
→ under_review
→ verified
→ rejected
→ needs_evidence
→ conflicted
→ superseded
```

Ràng buộc:

- AI chỉ được tạo `candidate`.
- Chỉ reviewer mới chuyển sang `verified`.
- `verified` không bị sửa nội dung trực tiếp; thay đổi tạo revision mới.
- `superseded` phải trỏ đến revision thay thế.

## 8.3. Evidence

```text
captured
→ validated
→ disputed
→ invalid
```

## 8.4. Behavioral test

```text
draft
→ approved
→ executed
→ passed | failed | blocked
```

---

# 9. Loại statement trong MVP

MVP hỗ trợ các type:

1. `business_rule`
2. `decision`
3. `state_transition`
4. `validation_constraint`
5. `data_transformation`
6. `calculation`
7. `authorization_rule`
8. `exception`
9. `external_effect`
10. `batch_or_schedule_behavior`
11. `terminology_definition`
12. `unknown_behavior`

Mỗi type có schema chung và trường mở rộng.

Ví dụ `business_rule`:

```json
{
  "id": "BST-0001",
  "type": "business_rule",
  "title": "VIP discount threshold",
  "statement": "Khách hàng VIP có đơn hàng lớn hơn 100000 nhận chiết khấu 8%.",
  "structured_expression": {
    "when": [
      {"field": "CUSTOMER_TYPE", "operator": "eq", "value": "VIP"},
      {"field": "ORDER_AMOUNT", "operator": "gt", "value": 100000}
    ],
    "then": [
      {"field": "DISCOUNT_RATE", "operator": "set", "value": 0.08}
    ]
  },
  "scope": {
    "system": "ORDER_MAINFRAME",
    "module": "DISCOUNT"
  },
  "confidence": 0.91,
  "status": "candidate"
}
```

Structured expression là optional. Natural-language statement là bắt buộc.

---

# 10. Data model tối thiểu

## 10.1. Project

- id
- name
- description
- organization_name
- legacy_system_name
- source_type
- snapshot_date
- status
- created_at
- updated_at
- created_by

## 10.2. SourceArtifact

- id
- project_id
- path
- filename
- extension
- mime_type
- size_bytes
- encoding
- sha256
- line_count
- storage_path
- ingest_status
- analysis_status
- created_at

## 10.3. SourceChunk

- id
- artifact_id
- start_line
- end_line
- content
- content_hash
- chunk_type
- parent_chunk_id nullable

## 10.4. BusinessStatement

- id
- project_id
- type
- title
- statement_text
- structured_expression_json
- scope_json
- confidence
- status
- extraction_method
- revision_no
- supersedes_id nullable
- created_by
- created_at
- updated_at

## 10.5. Evidence

- id
- project_id
- statement_id
- artifact_id
- chunk_id nullable
- start_line
- end_line
- excerpt
- evidence_type
- relation_type
- confidence
- status
- note
- created_by
- created_at

## 10.6. ReviewDecision

- id
- statement_id
- reviewer_id
- action
- reason
- previous_status
- new_status
- metadata_json
- created_at

## 10.7. GlossaryTerm

- id
- project_id
- term
- definition
- scope_json
- synonyms_json
- status
- evidence_ids_json
- valid_from nullable
- valid_to nullable

## 10.8. Conflict

- id
- project_id
- conflict_type
- description
- status
- resolution
- created_at
- resolved_at nullable

## 10.9. ConflictStatementLink

- conflict_id
- statement_id
- role

## 10.10. BehavioralTest

- id
- project_id
- name
- description
- preconditions_json
- input_json
- expected_output_json
- scope_json
- status
- linked_statement_ids_json
- created_by
- created_at

## 10.11. AuditEvent

- id
- project_id
- actor_id
- event_type
- entity_type
- entity_id
- before_json
- after_json
- metadata_json
- created_at

## 10.12. User

- id
- email
- display_name
- password_hash
- role
- is_active
- created_at

---

# 11. API yêu cầu

Base URL: `/api/v1`

## Authentication

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

MVP dùng local authentication với secure password hash và HTTP-only cookie hoặc JWT.

## Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/{projectId}`
- `PATCH /projects/{projectId}`
- `POST /projects/{projectId}/archive`

## Source artifacts

- `POST /projects/{projectId}/artifacts/upload`
- `GET /projects/{projectId}/artifacts`
- `GET /projects/{projectId}/artifacts/{artifactId}`
- `GET /projects/{projectId}/artifacts/{artifactId}/content`
- `POST /projects/{projectId}/artifacts/{artifactId}/analyze`

## Analysis jobs

- `POST /projects/{projectId}/analysis-jobs`
- `GET /projects/{projectId}/analysis-jobs`
- `GET /projects/{projectId}/analysis-jobs/{jobId}`

## Statements

- `GET /projects/{projectId}/statements`
- `POST /projects/{projectId}/statements`
- `GET /projects/{projectId}/statements/{statementId}`
- `PATCH /projects/{projectId}/statements/{statementId}`
- `POST /projects/{projectId}/statements/{statementId}/review`
- `POST /projects/{projectId}/statements/{statementId}/revise`

## Evidence

- `POST /projects/{projectId}/statements/{statementId}/evidence`
- `GET /projects/{projectId}/statements/{statementId}/evidence`
- `PATCH /projects/{projectId}/evidence/{evidenceId}/status`

## Glossary

- CRUD `/projects/{projectId}/glossary`

## Conflicts

- CRUD `/projects/{projectId}/conflicts`
- `POST /projects/{projectId}/conflicts/{conflictId}/resolve`

## Behavioral tests

- CRUD `/projects/{projectId}/behavioral-tests`
- `POST /projects/{projectId}/behavioral-tests/{testId}/execute-manual`

## Export

- `POST /projects/{projectId}/exports`
- `GET /projects/{projectId}/exports/{exportId}/download`

## Dashboard

- `GET /projects/{projectId}/dashboard`

---

# 12. UI yêu cầu

## 12.1. Login

- Email.
- Password.
- Error message rõ ràng.
- Không để lộ tài khoản có tồn tại hay không.

## 12.2. Project list

- Tên.
- Hệ thống cũ.
- Trạng thái.
- Số artifact.
- Số verified statement.
- Updated time.
- Tạo project.

## 12.3. Project dashboard

Các card:

- Source artifacts.
- Analysis progress.
- Candidate by status.
- Conflict.
- Test coverage.

Các shortcut:

- Upload source.
- Run analysis.
- Review queue.
- Export.

## 12.4. Source explorer

Layout hai cột:

- Trái: file tree.
- Phải: source viewer có line number.

Chức năng:

- Search.
- Highlight evidence range.
- Xem candidate liên quan.
- Tạo statement thủ công từ selection.

## 12.5. Candidate queue

Table:

- ID.
- Type.
- Title.
- Confidence.
- Evidence count.
- Status.
- Module.
- Updated.

Filter theo type/status/confidence/module.

## 12.6. Statement detail

Ba vùng:

1. Statement và structured expression.
2. Evidence list/source excerpt.
3. Review history và unresolved questions.

Actions theo role.

## 12.7. Conflict workspace

Hiển thị các statement cạnh nhau, scope, evidence và execution priority nếu có.

## 12.8. Behavioral test workspace

Form nhập precondition/input/expected output, liên kết statement và ghi nhận kết quả manual.

## 12.9. Export screen

- Chọn project version.
- Validate trước export.
- Hiển thị warning.
- Download package.

---

# 13. AI adapter contract

AI adapter phải độc lập provider.

Interface logic:

```typescript
interface AIExtractionAdapter {
  analyzeSource(input: SourceAnalysisInput): Promise<SourceAnalysisResult>;
}
```

Input:

```json
{
  "project_context": {
    "project_id": "P-001",
    "legacy_system_name": "ORDER_MAINFRAME",
    "language_hint": "COBOL"
  },
  "source": {
    "artifact_id": "A-001",
    "path": "src/DISCOUNT01.cbl",
    "start_line": 1200,
    "end_line": 1320,
    "content": "..."
  },
  "known_project_terms": [],
  "requested_statement_types": [
    "business_rule",
    "decision",
    "state_transition",
    "calculation",
    "exception",
    "unknown_behavior"
  ]
}
```

Output phải qua JSON Schema validation:

```json
{
  "candidates": [
    {
      "type": "business_rule",
      "title": "Candidate title",
      "statement": "Natural language statement",
      "structured_expression": {},
      "scope": {},
      "confidence": 0.0,
      "evidence_ranges": [
        {
          "start_line": 1240,
          "end_line": 1257,
          "reason": "Direct condition and assignment"
        }
      ],
      "unresolved_questions": [],
      "warnings": []
    }
  ]
}
```

Quy tắc:

- AI không được ghi trực tiếp database.
- AI output luôn là candidate.
- Output invalid schema bị reject.
- Không gửi toàn bộ project nếu không cần.
- API key lưu qua environment hoặc secret store.
- Log không được chứa source code nhạy cảm ở production mode.

---

# 14. Static extraction rules cho MVP

MVP cần deterministic extractor tối thiểu để không phụ thuộc hoàn toàn vào AI.

Các pattern:

- `IF ... THEN ... ELSE`
- `EVALUATE ... WHEN`
- So sánh `=`, `>`, `<`, `>=`, `<=`
- Assignment `MOVE`, `COMPUTE`, `SET`
- SQL data access.
- Procedure call.
- Status literals.
- Error code.
- Date threshold.
- Numeric threshold.
- Authorization-like check dựa trên user/role code.
- Comment gần logic.

Output deterministic cũng là candidate và ghi `extraction_method=static`.

---

# 15. Security yêu cầu

1. Chặn ZIP bomb và path traversal.
2. Giới hạn dung lượng upload cấu hình được.
3. Không execute source code upload.
4. Content được xem như untrusted text.
5. HTML escape mọi source excerpt.
6. RBAC kiểm tra ở backend.
7. Audit review và export.
8. Password dùng Argon2 hoặc bcrypt.
9. Secret không ghi vào repository.
10. CORS giới hạn.
11. Rate limiting cho login và AI analysis.
12. File storage path không dựa trực tiếp vào filename người dùng.
13. Export package phải loại bỏ secret.
14. Có cơ chế xóa project vật lý dành cho admin, nhưng không nằm trong UI MVP nếu chưa kiểm soát đủ.

---

# 16. Yêu cầu phi chức năng

## Performance

- Danh sách 10.000 statement vẫn phân trang được.
- Mở source file dưới 2 MB trong dưới 2 giây ở môi trường local.
- Giới hạn upload mặc định của MVP là 20 MB, có thể tăng bằng cấu hình môi trường.
- Upload 100 MB có progress được defer sang Phase 7 hoặc post-MVP theo quyết định Product Owner ngày 2026-08-06.
- Analysis job chạy bất đồng bộ.

## Reliability

- Analysis job idempotent theo artifact hash và analyzer version.
- Retry không tạo candidate trùng không kiểm soát.
- Database transaction cho review transition.
- Export tạo snapshot nhất quán.

## Maintainability

- Modular monolith.
- Strict typed schema.
- Migration database được version hóa.
- Business state machine tách khỏi controller.
- AI adapter tách khỏi extraction orchestration.

## Portability

- Chạy bằng Docker Compose.
- Hỗ trợ PostgreSQL.
- Local development có thể dùng PostgreSQL container.
- Không phụ thuộc cloud vendor.

## Observability

- Structured log.
- Request ID.
- Analysis job log.
- Error log không lộ source content mặc định.
- Health endpoint.

---

# 17. Kiến trúc MVP đề xuất

```text
Web UI
   ↓
REST API
   ↓
Application Services
   ├── Project Service
   ├── Ingestion Service
   ├── Analysis Orchestrator
   ├── Statement Service
   ├── Review Service
   ├── Conflict Service
   ├── Test Service
   └── Export Service
   ↓
Domain Layer
   ├── State machines
   ├── Validation rules
   └── Audit policies
   ↓
Infrastructure
   ├── PostgreSQL
   ├── Local/S3-compatible storage
   ├── Background worker
   └── AI adapters
```

Stack đề xuất:

- Backend: Python 3.12 + FastAPI.
- Validation: Pydantic v2.
- ORM: SQLAlchemy 2.
- Migration: Alembic.
- Database: PostgreSQL 16.
- Background jobs: Dramatiq hoặc Celery; MVP ưu tiên Dramatiq + Redis.
- Frontend: React + TypeScript + Vite.
- UI: component library nhẹ; không cần custom design system.
- Testing: pytest, Playwright.
- Packaging: Docker Compose.
- Storage MVP: local volume abstraction, interface sẵn cho S3-compatible.

Có thể chọn Node.js/NestJS nếu đội code quen TypeScript hơn, nhưng chỉ dùng một stack duy nhất.

---

# 18. Project structure đề xuất

```text
business-forensics/
├── apps/
│   ├── api/
│   ├── worker/
│   └── web/
├── packages/
│   ├── domain/
│   ├── schemas/
│   ├── extraction/
│   ├── ai_adapters/
│   └── export_format/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── sample_data/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 19. Acceptance criteria MVP

MVP được chấp nhận khi:

1. Người dùng đăng nhập và tạo project.
2. Upload ZIP chứa ít nhất 20 file source.
3. Hệ thống tạo inventory với hash và line count.
4. Người dùng chạy static analysis.
5. Hệ thống tạo candidate có evidence line range.
6. Có thể chạy AI-assisted extraction bằng adapter mock hoặc provider thật.
7. Reviewer xem evidence và confirm một candidate.
8. Candidate chỉ chuyển sang verified sau review action hợp lệ.
9. Reviewer có thể reject hoặc yêu cầu evidence.
10. Có thể tạo conflict giữa hai statement.
11. Có thể tạo behavioral test từ verified statement.
12. Dashboard phản ánh đúng số liệu.
13. Export ZIP chứa đầy đủ JSON package.
14. Import/export schema có version.
15. Audit log ghi lại create, analysis, review, conflict resolution và export.
16. Unit và integration test cho state transitions.
17. E2E test cho happy path.
18. Không có source file nào được execute.
19. Dự án chạy bằng `docker compose up`.
20. README có hướng dẫn setup và demo.

---

# 20. Test cases bắt buộc

## TC-01 Upload ZIP path traversal

ZIP chứa `../../evil.txt`.

Kết quả: reject entry, ghi warning, không ghi ra ngoài storage root.

## TC-02 Duplicate analysis

Chạy analysis hai lần với cùng artifact hash và analyzer version.

Kết quả: không tạo duplicate candidate; trả lại job/result đã tồn tại hoặc tạo revision có lý do rõ ràng.

## TC-03 AI invalid output

AI trả JSON sai schema.

Kết quả: job `failed_validation`; không ghi candidate.

## TC-04 AI cannot verify

AI output chứa status `verified`.

Kết quả: backend cưỡng chế thành `candidate` hoặc reject payload.

## TC-05 Human verify

Reviewer confirm candidate có evidence hợp lệ.

Kết quả: status `verified`, có ReviewDecision và AuditEvent.

## TC-06 Missing evidence

Reviewer confirm candidate không có evidence.

Kết quả: reject action với validation error.

## TC-07 Verified edit

Analyst sửa trực tiếp verified statement.

Kết quả: không cho sửa inplace; yêu cầu tạo revision.

## TC-08 Conflict preservation

Hai verified statement có điều kiện chồng lấn.

Kết quả: cho phép tạo conflict; không tự chọn statement thắng.

## TC-09 Export reproducibility

Export project hai lần không thay đổi dữ liệu.

Kết quả: nội dung logical giống nhau; metadata thời gian có thể khác nếu được tách khỏi deterministic content.

## TC-10 RBAC

Viewer gọi review endpoint.

Kết quả: HTTP 403.

---

# 21. Seed data demo

Project demo: `Legacy Purchase Approval`.

Source package giả lập gồm:

- `PURCHASE01.cbl`
- `APPROVAL.cbl`
- `LIMITS.cpy`
- `PURCHASE_SCHEMA.sql`
- `operating_notes.md`

Các rule mẫu:

1. Đề nghị dưới 100 triệu được trưởng phòng duyệt.
2. Đề nghị từ 100 triệu cần giám đốc duyệt.
3. Phòng khẩn cấp có override riêng.
4. Cuối tháng áp dụng hạn mức khác.
5. Một rule cũ mâu thuẫn nhưng chưa xác định còn hiệu lực.

Mục đích demo:

- Candidate.
- Exception.
- Conflict.
- Temporal scope.
- Human review.
- Behavioral test.

---

# 22. Definition of Done

Một feature chỉ hoàn tất khi:

- Có schema.
- Có migration.
- Có backend validation.
- Có authorization.
- Có audit nếu thay đổi state.
- Có unit test.
- Có integration test nếu chạm database/API.
- Có UI state loading/error/empty.
- Có tài liệu API.
- Không làm AI output trở thành verified knowledge trực tiếp.

---

# 23. Hướng dẫn cho AI coder

AI coder phải tuân thủ:

1. Không mở rộng ngoài MVP nếu chưa có requirement.
2. Không tạo “industry ontology”.
3. Không thêm auto-merge candidate.
4. Không tự động gọi verified.
5. Không thực thi code upload.
6. Không hardcode một AI provider.
7. Không dùng graph database trong MVP.
8. Không xây microservices.
9. Không bỏ audit để “làm nhanh”.
10. Mỗi sprint phải có runnable increment.
11. Mọi assumption chưa có trong tài liệu phải ghi vào `docs/assumptions.md`.
12. Không tự đổi state model.
13. Không dùng source code khách hàng để fine-tune.
14. Không log prompt/source đầy đủ ở chế độ production.
15. Ưu tiên correctness và traceability hơn UI đẹp.

---

# 24. Sprint đề xuất

## Sprint 0 — Foundation

- Repo.
- Docker Compose.
- Auth.
- Database.
- Migration.
- Project CRUD.
- CI test.

## Sprint 1 — Ingestion

- Upload.
- ZIP safety.
- Artifact inventory.
- Source viewer.
- Hash.
- Audit.

## Sprint 2 — Static extraction

- Chunking.
- Deterministic extractor.
- Candidate.
- Evidence.
- Candidate queue.

## Sprint 3 — Review workflow

- State machine.
- Review actions.
- Revision.
- RBAC.
- Audit.

## Sprint 4 — AI adapter

- Adapter interface.
- Mock adapter.
- Một provider adapter.
- JSON Schema enforcement.
- Job queue.

## Sprint 5 — Conflict và glossary

- Glossary.
- Conflict.
- Side-by-side review.

## Sprint 6 — Behavioral tests và export

- Test case.
- Manual execution.
- Export package.
- Dashboard.
- E2E demo.

---

# 25. Kết quả MVP mong đợi

MVP không nhằm chứng minh rằng AI có thể hiểu hoàn toàn một hệ thống legacy.

MVP nhằm chứng minh bốn điều:

1. Có thể trích xuất candidate knowledge từ source.
2. Có thể gắn mọi candidate với evidence cụ thể.
3. Có thể quản lý bất định và review mà không để AI tự biến suy diễn thành sự thật.
4. Có thể tạo một gói tri thức có version, traceable và dùng được làm nền cho modernization.
