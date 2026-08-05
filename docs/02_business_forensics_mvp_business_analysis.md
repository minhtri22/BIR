# BUSINESS FORENSICS PLATFORM
## Business Analysis Specification for MVP
**Document ID:** BFP-BA-001  
**Version:** 0.1  
**Status:** Draft for MVP implementation and product validation  
**Purpose:** Mô tả nhu cầu kinh doanh, nghiệp vụ mục tiêu, quy tắc, luồng công việc và giới hạn của MVP.

---

# 1. Bối cảnh kinh doanh

Doanh nghiệp có hệ thống legacy đã vận hành ổn định trong thời gian dài thường muốn chuyển sang nền tảng mới vì:

- Công nghệ cũ khó mở rộng.
- Thiếu nhân sự duy trì.
- Chi phí hạ tầng và license tăng.
- Khó tích hợp API, mobile, cloud hoặc AI.
- Kiến trúc cũ làm chậm thay đổi.
- Nhà cung cấp hoặc stack công nghệ tạo vendor lock-in.
- Rủi ro ngừng hỗ trợ.
- Yêu cầu bảo mật và tuân thủ mới.

Tuy nhiên, tài sản quan trọng nhất của hệ thống cũ không phải source code mà là hành vi nghiệp vụ được tích lũy qua nhiều năm:

- Rule.
- Quyết định.
- Trạng thái.
- Ngoại lệ.
- Thứ tự ưu tiên.
- Quyền override.
- Cách tính toán.
- Quy tắc dữ liệu.
- Tương tác với hệ thống khác.
- Các xử lý cuối ngày, cuối tháng, cuối năm.
- Những hành vi chỉ xuất hiện trong tình huống hiếm.

Các dự án modernization thất bại khi chuyển được code nhưng làm mất hoặc thay đổi hành vi này.

---

# 2. Business need

Doanh nghiệp cần một cách đáng tin cậy để trả lời:

1. Hệ thống cũ đang thực sự làm gì?
2. Mỗi phát biểu nghiệp vụ dựa trên bằng chứng nào?
3. Phần nào đã được xác nhận, phần nào chỉ là giả thuyết?
4. Các ngoại lệ và override nằm ở đâu?
5. Có rule mâu thuẫn hoặc chồng lấn không?
6. Nếu chuyển sang hệ thống mới, cần kiểm thử hành vi nào?
7. Những tri thức nào vẫn chưa được hiểu?
8. Ai đã xác nhận từng kết luận và vào thời điểm nào?

---

# 3. Product vision

> Business Forensics Platform giúp một doanh nghiệp cụ thể tái dựng hành vi nghiệp vụ của hệ thống legacy dựa trên bằng chứng, quản lý bất định và xác nhận của con người, nhằm tạo nền tảng an toàn cho quá trình modernization.

Sản phẩm không tuyên bố:

- Hiểu nghiệp vụ tốt hơn doanh nghiệp.
- Xác định best practice.
- Chuẩn hóa quy trình.
- Tự quyết định rule nào nên giữ.
- Tự thay thế chuyên gia nghiệp vụ.
- Tự bảo đảm toàn bộ hệ thống đã được hiểu.

---

# 4. Business outcomes

## 4.1. Giảm rủi ro mất nghiệp vụ

Mỗi rule quan trọng có:

- Evidence.
- Reviewer.
- Status.
- Scope.
- Test case.

## 4.2. Giảm phụ thuộc vào cá nhân

Tri thức không chỉ nằm trong đầu một chuyên gia hoặc lập trình viên legacy.

## 4.3. Tăng khả năng audit

Mỗi kết luận có thể truy ngược về nguồn và review decision.

## 4.4. Tạo đầu vào tốt hơn cho modernization

Đội triển khai có thể dùng verified statements và behavioral tests thay vì chỉ dựa vào code translation.

## 4.5. Giảm vendor lock-in tương lai

Tri thức nghiệp vụ được lưu trong format trung tính, không thuộc framework hoặc ngôn ngữ đích.

---

# 5. Stakeholder

## 5.1. Executive sponsor

Thường là CIO, CTO, Head of Transformation.

Quan tâm:

- Risk.
- Cost.
- Timeline.
- Audit.
- Modernization readiness.
- Vendor independence.

## 5.2. Program manager

Quản lý tiến độ discovery và review.

Quan tâm:

- Coverage.
- Blocker.
- Review backlog.
- Conflict.
- Export readiness.

## 5.3. Legacy technical expert

Hiểu source, batch, database và integration.

Quan tâm:

- Độ chính xác của evidence.
- Execution order.
- Data dependency.
- Dead code.
- Technical context.

## 5.4. Business SME

Hiểu cách nghiệp vụ được vận hành.

Quan tâm:

- Statement có phản ánh đúng thực tế không.
- Scope và ngoại lệ.
- Ý nghĩa thuật ngữ.
- Lý do tồn tại của rule.
- Chính sách hiện còn hiệu lực hay không.

## 5.5. Modernization architect

Dùng output để thiết kế target.

Quan tâm:

- Rule.
- State.
- Data transformation.
- External effect.
- Tests.
- Traceability.

## 5.6. Auditor hoặc Risk/Compliance

Quan tâm:

- Provenance.
- Approval.
- Change history.
- Conflict.
- Evidence integrity.

---

# 6. Giá trị sản phẩm theo stakeholder

| Stakeholder | Giá trị chính |
|---|---|
| Executive sponsor | Biết mức độ rủi ro trước khi rewrite hoặc migration |
| Program manager | Quản lý backlog tri thức và review |
| Legacy expert | Chuyển hiểu biết kỹ thuật thành evidence có cấu trúc |
| Business SME | Xác nhận nghiệp vụ bằng ngôn ngữ dễ hiểu |
| Architect | Nhận đầu vào trung tính cho target design |
| Auditor | Có traceability và approval history |

---

# 7. Business capability MVP

MVP cần sáu capability:

1. **Source Evidence Management**
2. **Candidate Knowledge Extraction**
3. **Human Review and Promotion**
4. **Uncertainty and Conflict Management**
5. **Behavioral Test Definition**
6. **Traceable Knowledge Export**

Không xây capability “automatic modernization” trong MVP.

---

# 8. Business process tổng thể

```text
Khởi tạo project
    ↓
Nhập source snapshot
    ↓
Kiểm kê và xác thực artifact
    ↓
Phân tích deterministic/AI-assisted
    ↓
Tạo candidate statement
    ↓
Gắn evidence và unresolved question
    ↓
Analyst triage
    ↓
Technical review
    ↓
Business review
    ↓
Verified / Rejected / Needs evidence / Conflict
    ↓
Tạo behavioral test
    ↓
Đánh giá coverage và unresolved risk
    ↓
Export knowledge package
```

---

# 9. Business process chi tiết

## BP-01 Project initiation

### Trigger

Một modernization assessment bắt đầu.

### Input

- Tên hệ thống.
- Scope.
- Snapshot date.
- Source package.
- Danh sách reviewer.

### Output

- Project charter tối thiểu.
- Project ID.
- Scope statement.
- Initial audit record.

### Business rules

- Một project đại diện cho một scope hệ thống và một snapshot cụ thể.
- Nếu source thay đổi đáng kể, phải tạo snapshot/revision mới.
- Không trộn source từ nhiều version mà không ghi metadata.

---

## BP-02 Source ingestion

### Trigger

Analyst upload source.

### Activities

1. Kiểm tra định dạng.
2. Tính hash.
3. Ghi inventory.
4. Phân loại.
5. Xác định file không đọc được.
6. Tạo ingest report.

### Business rules

- Artifact gốc immutable.
- Mọi evidence phải trỏ đến artifact hash.
- File duplicate được nhận biết bằng hash.
- Không execute source.
- File không đọc được không bị bỏ im lặng; phải có warning.

---

## BP-03 Candidate extraction

### Trigger

Analyst bắt đầu analysis job.

### Activities

1. Chunk source.
2. Static extractor tìm pattern.
3. AI adapter đề xuất statement.
4. Validate schema.
5. Dedupe kỹ thuật ở mức cùng artifact/chunk/analyzer version.
6. Ghi candidate và evidence.

### Business rules

- Candidate không phải sự thật đã xác nhận.
- AI không được tự promote.
- Confidence là mức độ tự tin của extractor, không phải xác suất nghiệp vụ đúng.
- Candidate không evidence có thể được lưu dưới type `unknown_behavior`, nhưng không thể verify cho đến khi có evidence hoặc justification được phê duyệt.
- Không sử dụng knowledge từ customer khác làm fact.

---

## BP-04 Analyst triage

### Trigger

Candidate mới được tạo.

### Activities

- Kiểm tra statement có đọc được không.
- Kiểm tra evidence range.
- Sửa cách diễn đạt nếu cần.
- Gắn scope ban đầu.
- Thêm unresolved question.
- Gửi review.

### Business rules

- Analyst được sửa candidate trước review.
- Mọi sửa đổi quan trọng phải audit.
- Analyst không được verify nếu không có quyền reviewer.
- Không được xóa candidate để che mất sai sót; dùng rejected hoặc superseded.

---

## BP-05 Technical review

### Mục tiêu

Xác nhận mapping statement–source.

### Reviewer kiểm tra

- Evidence đúng đoạn code chưa.
- Có path khác thay đổi kết quả không.
- Thứ tự thực thi.
- Variable mapping.
- Gọi procedure/module khác.
- Transaction hoặc batch context.
- Rule có thể là dead code không.
- Scope và effective period.

### Output

- Technical accepted.
- Needs more evidence.
- Conflict.
- Rejected.

MVP có thể dùng một review state chung, nhưng review decision phải ghi loại reviewer.

---

## BP-06 Business review

### Mục tiêu

Xác nhận statement có phản ánh cách doanh nghiệp hiểu và sử dụng hệ thống hay không.

### Reviewer kiểm tra

- Thuật ngữ.
- Ý nghĩa.
- Scope tổ chức.
- Ngoại lệ.
- Trạng thái hiệu lực.
- Lý do nghiệp vụ nếu biết.
- Tác động.

### Output

- Verified.
- Rejected.
- Needs evidence.
- Conflict.
- Obsolete but historically valid.

### Business rule

“Obsolete” không đồng nghĩa với “không từng tồn tại”. MVP có thể lưu `obsolete_candidate` trong metadata hoặc conflict/resolution; bản sau nên có temporal model đầy đủ.

---

## BP-07 Conflict handling

### Trigger

Hai hoặc nhiều statement không thể đồng thời đúng trong cùng scope, hoặc chưa rõ priority.

### Activities

1. Tạo conflict.
2. Liên kết statement.
3. Mô tả conflict.
4. Xác định loại conflict.
5. Thu thập thêm evidence.
6. Review.
7. Resolve hoặc để unresolved.

### Resolution examples

- Khác business unit.
- Khác thời kỳ.
- Khác channel.
- Override priority.
- Một statement sai.
- Cả hai đều đúng trong điều kiện khác nhau.
- Không đủ evidence.

### Business rule

Hệ thống không tự động chọn winner.

---

## BP-08 Behavioral test definition

### Trigger

Statement được verify hoặc cần test để xác minh.

### Activities

- Xác định precondition.
- Xác định input.
- Xác định expected output/effect.
- Liên kết statement.
- Review test.

### Business rules

- Một test có thể liên kết nhiều statement.
- Test phải ghi rõ scope.
- Expected output có thể là data, state, decision, message hoặc external effect.
- Test thất bại không tự động làm statement invalid; cần review nguyên nhân.

---

## BP-09 Export readiness

### Trigger

Project cần bàn giao cho đội modernization.

### Checks

- Verified statement có evidence.
- Verified rule quan trọng có test hoặc documented exception.
- Conflict critical đã resolve hoặc được ghi nhận rủi ro.
- Source inventory hoàn tất trong scope.
- Audit log không lỗi.
- Export schema version hợp lệ.

### Output

- Export-ready.
- Export with warnings.
- Blocked.

MVP không cần tính “100% understood”. Chỉ xác nhận hồ sơ đã đạt điều kiện xuất theo scope đã khai báo.

---

# 10. Business object model

## 10.1. Project

Đơn vị quản lý discovery.

## 10.2. Source Artifact

Bản sao bất biến của một file hoặc nguồn evidence.

## 10.3. Source Chunk

Đoạn source dùng để phân tích và trích dẫn.

## 10.4. Candidate Statement

Phát biểu được đề xuất nhưng chưa xác nhận.

## 10.5. Verified Statement

Revision của statement đã qua review hợp lệ.

## 10.6. Evidence

Liên kết giữa statement và nguồn chứng minh.

## 10.7. Review Decision

Hành động của con người đối với statement.

## 10.8. Glossary Term

Định nghĩa thuật ngữ riêng trong phạm vi project.

## 10.9. Conflict

Bản ghi mâu thuẫn hoặc chưa rõ.

## 10.10. Behavioral Test

Tình huống có input và expected behavior.

## 10.11. Audit Event

Bản ghi thay đổi không thể sửa bằng UI thông thường.

---

# 11. Information classification

## 11.1. Observed fact

Thông tin trực tiếp từ artifact hoặc trace.

Ví dụ:

- Code so sánh `CUSTOMER_TYPE = "VIP"`.
- Module ghi `DISCOUNT_RATE = 0.08`.

## 11.2. Candidate interpretation

Diễn giải chưa xác nhận:

> Khách VIP nhận chiết khấu 8%.

## 11.3. Verified business statement

Candidate đã được reviewer xác nhận trong một scope cụ thể.

## 11.4. Human rationale

Lý do hoặc mục đích được SME giải thích.

Không được coi rationale là observed fact nếu không có bằng chứng khác.

## 11.5. Unknown

Không đủ thông tin để diễn giải.

## 11.6. Conflict

Có nhiều cách diễn giải hoặc evidence không nhất quán.

---

# 12. Core business rules

## BR-001

Mọi verified statement phải có ít nhất một evidence hợp lệ.

## BR-002

AI và static extractor chỉ được tạo candidate.

## BR-003

Confidence không được dùng thay cho human review.

## BR-004

Không xóa lịch sử review.

## BR-005

Verified statement không được sửa trực tiếp; phải tạo revision.

## BR-006

Mỗi evidence phải trỏ đến artifact hash và vị trí nguồn.

## BR-007

Không tự động merge các statement giống nhau nếu scope hoặc evidence khác nhau.

## BR-008

Một statement hiếm không bị giảm giá trị chỉ vì ít xuất hiện.

## BR-009

Conflict được bảo tồn cho đến khi có resolution có reviewer.

## BR-010

Knowledge của một project không được sử dụng như fact trong project khác.

## BR-011

Template ngành, nếu có về sau, chỉ là checklist hoặc external reference.

## BR-012

Export phải ghi schema version và project snapshot.

## BR-013

Mọi state transition quan trọng phải tạo audit event.

## BR-014

Dead-code suspicion phải được ghi là suspicion, không phải kết luận.

## BR-015

Một statement có thể hợp lệ ở quá khứ nhưng không còn hiệu lực; không được xóa lịch sử.

## BR-016

Thiếu tài liệu không chứng minh rằng hành vi không tồn tại.

## BR-017

Không có production trace không đồng nghĩa rule không được sử dụng.

## BR-018

Hệ thống không được tự đề xuất tối ưu hóa nghiệp vụ trong MVP.

---

# 13. Decision table cho review

| Điều kiện | Action |
|---|---|
| Có evidence, statement rõ, reviewer đồng ý | Verified |
| Evidence sai hoặc statement diễn giải sai | Rejected |
| Có dấu hiệu đúng nhưng thiếu path/context | Needs evidence |
| Có statement khác chồng lấn/mâu thuẫn | Conflicted |
| Statement cũ được thay bằng revision mới | Superseded |
| AI trả confidence cao nhưng chưa review | Vẫn là Candidate |
| Rule hiếm và chưa rõ còn hiệu lực | Needs evidence hoặc Conflict, không tự reject |

---

# 14. Scope model

Mỗi statement có thể áp dụng theo:

- Organization.
- Business unit.
- Department.
- Branch.
- Product.
- Customer segment.
- Channel.
- Geography.
- System/module.
- Process step.
- Effective date.
- Batch/window.
- User/role.
- Data condition.

MVP lưu scope dưới JSON nhưng UI chỉ cần hỗ trợ các trường phổ biến:

- system
- module
- business_unit
- effective_from
- effective_to
- free_text_scope

---

# 15. Evidence model

Các evidence type MVP:

- `source_code`
- `sql`
- `configuration`
- `documentation`
- `sample_data`
- `manual_observation`
- `reviewer_statement`

Mức độ evidence không mặc định giống nhau. MVP chưa cần scoring phức tạp, nhưng phải lưu type và reviewer có thể đánh dấu disputed.

Relation type:

- `supports`
- `implements`
- `contradicts`
- `contextualizes`
- `suggests`
- `references`

---

# 16. Uncertainty model

Mỗi candidate có thể có:

- Confidence số 0–1.
- Unresolved questions.
- Warning.
- Unknown fields.
- Alternative interpretation.
- Missing dependency.
- Suspected dead code.
- Scope ambiguity.

Không được chuyển tất cả thành một confidence score duy nhất.

---

# 17. KPI cho PoC/MVP

Các KPI không nhằm đánh giá AI “hiểu nghiệp vụ hoàn toàn”.

## Product KPI

- Thời gian từ upload đến candidate đầu tiên.
- Tỷ lệ candidate có evidence hợp lệ.
- Thời gian review trung bình.
- Tỷ lệ candidate cần thêm evidence.
- Số conflict được phát hiện.
- Tỷ lệ verified statement có behavioral test.
- Số lần truy ngược statement về source thành công.
- Tỷ lệ AI output bị schema reject.

## Validation KPI

- Reviewer agreement giữa technical reviewer và business SME.
- False statement rate trên bộ demo đã gán nhãn.
- Evidence range precision trên bộ demo.
- Duplicate candidate rate.
- Revision rate sau verification.
- Tỷ lệ unresolved critical statements.

## Không dùng làm KPI MVP

- Số dòng code phân tích như thước đo giá trị chính.
- Số candidate càng nhiều càng tốt.
- Confidence trung bình càng cao càng tốt.
- 100% automation.
- 100% coverage nghiệp vụ.

---

# 18. Rủi ro nghiệp vụ

## Risk 1 — AI hallucination

Mitigation:

- Structured output.
- Evidence requirement.
- Human gate.
- Candidate status.
- Audit.

## Risk 2 — Reviewer rubber-stamping

Mitigation:

- Bắt nhập reason cho review quan trọng.
- Hiển thị evidence trước action.
- Audit reviewer.
- Sampling audit về sau.

## Risk 3 — Scope bị hiểu sai

Mitigation:

- Scope field.
- Conflict.
- Unresolved question.
- Revision.

## Risk 4 — Missing paths

Mitigation:

- Coverage dashboard.
- Static dependency references.
- Không tuyên bố completeness.

## Risk 5 — Confidential source leakage

Mitigation:

- Local deployment option.
- Provider abstraction.
- Data minimization.
- No training by default.
- Secure storage.

## Risk 6 — Tool bị dùng để “chứng minh” migration đúng khi chưa đủ evidence

Mitigation:

- Export readiness warning.
- Không có nhãn “fully equivalent”.
- Behavioral tests chỉ là documented tests, không phải formal proof.

## Risk 7 — Industry bias

Mitigation:

- Project-isolated semantics.
- Không cross-customer fact learning.
- Meta-model trung tính.
- External template phải được đánh dấu.

---

# 19. Assumptions MVP

1. Source package chủ yếu là text.
2. Người dùng có quyền hợp pháp để upload và phân tích source.
3. Có ít nhất một reviewer hiểu code hoặc nghiệp vụ.
4. MVP chạy trong môi trường kiểm soát.
5. Số user đồng thời thấp.
6. Project demo không dùng dữ liệu production nhạy cảm.
7. Một AI provider hoặc mock adapter đủ cho MVP.
8. Mục tiêu là chứng minh workflow, không chứng minh parser hoàn chỉnh.

---

# 20. Constraints

- Ngân sách và đội phát triển hạn chế.
- Không xây compiler legacy hoàn chỉnh.
- Không phụ thuộc một cloud.
- Không xây graph database ở MVP.
- Không triển khai nhiều AI provider cùng lúc.
- Không xây multi-language UI ngoài tiếng Việt/English cơ bản.
- Không xử lý binary proprietary formats trong MVP.

---

# 21. Product validation plan

## Hypothesis H1

Modernization team xem việc gắn evidence và review state hữu ích hơn báo cáo code analysis thông thường.

Cách kiểm chứng:

- Demo với 3–5 chuyên gia modernization.
- Cho review 10 candidate.
- Đo thời gian và phản hồi.

## H2

Business SME có thể hiểu và xác nhận statement nếu được trình bày cùng evidence và glossary.

Cách kiểm chứng:

- User test với SME.
- Đo tỷ lệ statement hiểu đúng.
- Thu thập điểm khó.

## H3

Conflict và uncertainty là giá trị, không phải yếu điểm UX.

Cách kiểm chứng:

- Cho người dùng xem case mâu thuẫn.
- Hỏi liệu record conflict giúp ra quyết định hơn việc AI tự hợp nhất.

## H4

Verified statement + behavioral test là đầu vào có giá trị cho đội target architecture.

Cách kiểm chứng:

- Cho architect dùng export package để thiết kế một module target nhỏ.
- Đánh giá mức giảm clarification loop.

---

# 22. Demo scenario chuẩn

## Legacy purchase approval

Source thể hiện:

- Trưởng phòng duyệt dưới ngưỡng.
- Giám đốc duyệt trên ngưỡng.
- Một phòng ban có override.
- Một rule cuối tháng khác.
- Một đoạn code cũ có vẻ mâu thuẫn.
- SQL update trạng thái.
- Một procedure gửi thông báo.

Demo flow:

1. Upload ZIP.
2. Inventory.
3. Static analysis.
4. AI candidate.
5. Xem evidence.
6. Verify rule cơ bản.
7. Mark needs evidence cho override.
8. Tạo conflict.
9. Tạo test case.
10. Export.

Demo phải nhấn mạnh:

- Hệ thống không tự kết luận.
- Hệ thống bảo tồn ngoại lệ.
- Hệ thống truy ngược nguồn.
- Human confirmation là gate bắt buộc.

---

# 23. Business acceptance criteria

MVP đáp ứng nhu cầu nghiệp vụ khi:

1. Analyst có thể quản lý một source snapshot.
2. Reviewer không cần đọc toàn bộ project để review một candidate.
3. Mỗi verified statement truy được về evidence.
4. Candidate chưa review không bị hiển thị như sự thật.
5. Conflict được lưu độc lập.
6. Có thể biểu diễn uncertainty.
7. Có thể tạo test từ knowledge đã review.
8. Export không phụ thuộc AI provider.
9. Không có cross-project semantic contamination.
10. Audit trả lời được ai đã xác nhận điều gì.

---

# 24. Hướng phát triển sau MVP

Chỉ xem xét sau khi MVP được xác nhận:

- Parser sâu hơn cho COBOL/RPG/PL-I.
- Dynamic trace ingestion.
- Database lineage.
- UI/screen behavior capture.
- Temporal rule model.
- Formal decision tables.
- Behavioral equivalence execution.
- Target code generator.
- BIR specification.
- Business knowledge graph.
- Local/on-prem enterprise deployment.
- SSO và enterprise governance.
- Reviewer workflow nhiều cấp.
- Integration với Git, mainframe repo và CI.
- Export sang BPMN/DMN/OpenAPI khi phù hợp.

---

# 25. Kết luận nghiệp vụ

Sản phẩm MVP không bán khả năng “AI hiểu legacy code”.

Nó chứng minh một quy trình có kiểm soát:

> Source cũ được chuyển thành các phát biểu nghiệp vụ ứng viên, mỗi phát biểu có bằng chứng, bất định, review state và test case; chỉ tri thức đã được con người xác nhận mới trở thành đầu vào cho modernization.

Giá trị cốt lõi là **traceability và preservation**, không phải số lượng code được dịch tự động.
