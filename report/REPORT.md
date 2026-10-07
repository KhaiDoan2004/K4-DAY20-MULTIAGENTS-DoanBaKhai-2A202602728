# Báo cáo Lab: Self evolving Agentic

> Sao chép tệp này thành `report/REPORT.md` (đã làm ở Phần 0) và điền dần qua các Phần của lab. Xóa các dòng hướng dẫn dạng trích dẫn (bắt đầu bằng `>`). Văn phong kỹ thuật, ngắn gọn, mọi nhận định đi kèm số liệu hoặc bằng chứng. Trong buổi học: điền mục 1 đến 7 (bản nháp). Sau buổi học: hoàn thiện mục 8 đến 10.

## 1. Thông tin sinh viên và cấu hình

- Họ tên: Đoàn Bá Khải
- Mã sinh viên: 2A202602728

- Nhà cung cấp và mô hình (`LAB_MODEL`, không ghi khóa API), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: `openai:gpt-4o-mini`, `LAB_TEMPERATURE=0`, `recursion_limit=50`.
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, Linux (Ubuntu 24.04 LTS qua WSL2 trên Windows 11), chạy trực tiếp trong Python virtualenv (`.venv`).
- Số lần chạy tác vụ đã dùng / ngân sách: 6 / 22 (baseline: 3, subagents: 3).
- Commit của tag `freeze`: (sẽ điền ở Phần 4 sau khi đóng băng).

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

- H1 (subagents so với baseline): Dự đoán trên các tác vụ đánh giá (`*-eval`), điều kiện `subagents` không cải thiện điểm số đáng kể so với `baseline` (điểm tương đương hoặc chỉ nhỉnh hơn không quá 0.05) nhưng chi phí token sẽ cao hơn gấp 5 - 15 lần và độ trễ tăng cao. Căn cứ từ phân loại lỗi Mục 4: các lỗi chính thuộc nhóm G (vi phạm quy ước nội bộ `rule_*`) và nhóm D (dữ liệu bẩn); việc chia nhỏ cho subagent khi bị cô lập ngữ cảnh (context isolation) khiến subagent thiếu thông tin đặc tả và dễ lạc vào vòng lặp thử-sai (như đã thấy ở `data-learn` tiêu tốn 13.7M tokens), phù hợp với nghiên cứu của Anthropic (2024) về chi phí multi-agent.
- H2 (skills-auto so với baseline): Dự đoán điều kiện `skills-auto` sẽ đạt điểm số nhỉnh hơn hoặc tương đương `baseline` trên tác vụ đánh giá, nhưng hiệu quả bị giới hạn bởi tính khái quát của skill tự sinh và xác suất kích hoạt nạp skill. Căn cứ từ nghiên cứu SkillsBench (2024) và SkillEvolBench (2025): kỹ năng do LLM tự sinh từ feedback thường có xu hướng bám sát tập học (overfitting) và khó chuyển giao toàn diện sang tác vụ kiểm thử mới nếu các bài kiểm tra có đặc thù dữ liệu khác biệt.
- H3 (tác vụ học so với tác vụ đánh giá): Dự đoán điểm số trung bình trên tác vụ học (`*-learn`) sẽ cao hơn rõ rệt so với tác vụ đánh giá (`*-eval`) trên cả ba điều kiện thí nghiệm (chênh lệch dự kiến khoảng 0.10 - 0.20 điểm). Căn cứ: tác vụ học có cơ chế phản hồi `detail` từ bot chấm điểm giúp tác tử định hướng và cung cấp tư liệu cho curator tiến hóa; trong khi đó ở tác vụ đánh giá, trường `detail` hoàn toàn bị ẩn và các kịch bản kiểm thử có bộ dữ liệu độc lập mà tác tử chưa từng tiếp xúc.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Tác tử mặc định được cung cấp 9 công cụ:
   - Nhóm thao tác tệp: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`.
   - Nhóm thực thi shell: `execute`.
   - Nhóm ủy quyền tác tử con: `task`.
   Công cụ duy nhất cho phép chạy lệnh shell là `execute`.

2. Mô tả của công cụ `task` về subagent `general-purpose`:
   - Đây là tác tử đa năng dùng để nghiên cứu câu hỏi phức tạp, tìm kiếm tệp và nội dung, thực hiện tác vụ nhiều bước với toàn bộ công cụ như tác tử chính.
   - Về ngữ cảnh: Subagent mặc định hoàn toàn vô trạng thái (`stateless by default`). Nó chỉ nhìn thấy nội dung prompt mà tác tử chính truyền vào cho nó (`the agent sees only the prompt you give it and returns a single final report`), không thừa kế toàn bộ ngữ cảnh hội thoại của tác tử chính trừ khi được chỉ định rõ.

3. Trích dẫn câu hướng dẫn hành vi:
   - Từ mô tả công cụ `task`: *"Put full detail in the prompt and state exactly what it should return — unless an agent type below says it inherits your conversation instead."* (hoặc *"Tell the agent whether to create content, analyze, or only research, since it can't necessarily see the user's intent unless it inherits your conversation..."*).
   - Từ mô tả công cụ `execute`: *"You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search. Use read_file rather than cat/head/tail."*

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| `code-learn` | `tests_not_modified` | G, C | `detail`: *"the original files in tests/ must not be modified (new test files are allowed)"* (vết: agent sửa file tests có sẵn để ép pass). |
| `code-learn` | `parse_price_all_formats` | D | `detail`: *"wrong for: ['(12.00)']"* (chỉ xử lý `$` và dấu phẩy, bỏ sót format số âm kế toán dạng ngoặc đơn). |
| `code-learn` | `low_stock_follows_docstring` | A | `detail`: *"low_stock returned ['b', 'A', 'c']"* (bỏ qua quy tắc sắp xếp theo số lượng rồi theo SKU nêu trong docstring). |
| `code-learn` | `csv_quoting_follows_docstring` | A | `detail`: *"to_csv_row returned 'Desk, large \"oak\",10.00,2'"* (không escape dấu ngoặc kép theo chuẩn CSV RFC 4180). |
| `code-learn` | `rule_type_hints` | G | `detail`: *"RULE: every public function in the package has type annotations on all parameters and on the return value."* |
| `code-learn` | `rule_regression_tests` | G | `detail`: *"RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass."* |
| `code-learn` | `rule_changelog` | G | `detail`: *"RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets)."* |
| `data-learn` | `north_q1_revenue` | D, F | `detail`: *"north_q1_revenue: wrong value (got 0 / got 3015.5)"* (agent không xử lý timezone UTC và lọc sai quý 1). |
| `data-learn` | `missing_amount_orders` | D | `detail`: *"missing_amount_orders: wrong value (got 0)"* (không phát hiện giá trị sentinel `-999` là missing amount theo README). |
| `data-learn` | `rule_money_in_cents` | G | `detail`: *"RULE: money values in answer.json are integer cents (1606.67 USD is written 160667)."* |
| `data-learn` | `rule_meta_block` | G | `detail`: *"RULE: answer.json has an object `meta` = {"source": ..., "rows_in": ..., "rows_used": ...}."* |
| `data-learn` | `rule_clean_csv` | G | `detail`: *"RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents..."* |
| `logs-learn` | `entry_count` | D | `detail`: *"wrong number of entries (got 10)"* (bỏ qua dòng gộp `-- last message repeated N times --`). |
| `logs-learn` | `timestamps_utc` | F | `detail`: *"5/25 timestamps match"* (sai định dạng chuỗi timestamp UTC ISO-8601). |
| `logs-learn` | `rule_service_names` | G | `detail`: *"RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service)."* |
| `logs-learn` | `rule_sorted_errors` | G | `detail`: *"RULE: `errors` is sorted by service, then by timestamp_utc, ascending."* |
| `logs-learn` | `rule_schema_header` | G | `detail`: *"RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage"."* |

Nhận xét: nhóm lỗi chiếm đa số áp đảo là **Nhóm G (Vi phạm quy ước tổ chức Acme)** và **Nhóm D (Bỏ sót dữ liệu bẩn / biên)**. Tác tử chỉ chú ý giải quyết yêu cầu bề mặt mà hoàn toàn không tuân thủ các quy ước nội bộ của tổ chức (`rule_*`) do không được liệt kê cụ thể trong từng câu hỏi ngắn. **Skill hoàn toàn có thể phòng ngừa nhóm lỗi này**, vì skill đóng vai trò như SOP/playbook chuẩn hóa, định hướng tác tử kiểm tra các quy ước tổ chức (type hints, regression tests, changelog, money in cents, meta block, schema version) ngay từ bước đầu tiên.

## 5. Điều kiện `subagents` (Phần 2.3)

- Các subagent đã định nghĩa (tên, vai trò, lý do thiết kế):
  1. `explorer`: Chuyên đọc tài liệu, docstrings, cấu trúc thư mục, log và dữ liệu mẫu; báo cáo sự thật khách quan mà không sửa file, giúp tác tử chính hiểu rõ bối cảnh mà không bị phân tán.
  2. `reviewer`: Kiểm tra độc lập kết quả theo đề bài, chạy verify và soi xét các trường hợp biên, không sửa file; giúp phát hiện thiếu sót trước khi kết thúc tác vụ.
  3. `implementer`: Thực thi các thay đổi code/script cụ thể và chạy kiểm thử trong sandbox; giúp đóng gói việc triển khai thành tác vụ con độc lập.
- `subagent_calls` ở từng tác vụ và nhận xét (kể cả trường hợp bằng 0):
  - `code-learn`: 0 lần gọi. Tác tử chính tự nhận thấy có thể sửa code và chạy pytest trực tiếp (18 tool calls), không chủ động giao việc.
  - `data-learn`: 1 lần gọi (gọi subagent `implementer`). Tác tử chính sau khi thử chạy `import pandas` bị lỗi `ModuleNotFoundError` đã giao việc phân tích dữ liệu cho subagent `implementer`.
  - `logs-learn`: 0 lần gọi. Tác tử chính tự đọc log và tự sinh JSON (3 tool calls), xem đây là bước phân tích đơn lẻ nên không ủy quyền.
- Thông tin thiếu hoặc thừa khi giao việc (nếu có giao việc):
  - Ở `data-learn`, khi tác tử chính giao việc cho `implementer`, prompt giao việc chỉ nêu các tên khóa cơ bản (`north_q1_revenue`, `north_q1_orders`,...) nhưng **thiếu hoàn toàn các quy ước Acme** (`rule_money_in_cents`, `rule_meta_block`, `rule_clean_csv`). Do subagent bị cô lập ngữ cảnh (context isolation), nó không thể biết các quy ước này, dẫn đến kết quả đầu ra thiếu các trường bắt buộc của Acme.
- Ảnh hưởng đến token và thời gian:
  - Khi không gọi subagent (`code-learn`, `logs-learn`): Tiêu thụ 19k - 65k tokens, thời gian 13s - 63s (tương đương baseline).
  - Khi gọi subagent (`data-learn`): Tiêu thụ bùng nổ lên **13,767,312 tokens** (so với 25,617 tokens ở baseline, tăng hơn 530 lần!) và thời gian chạy kéo dài lên **1042.3s (~17.4 phút)**! Việc subagent tự xoay xở không có thư viện chuyên dụng và chạy nhiều vòng lặp thử-sai gây lãng phí tài nguyên cực kỳ lớn.

## 6. Self-evolving: skill do curator sinh (Phần 3)

- Số lần chạy curator, số skill bị xóa và lý do:
  - Chạy curator 2 lần: Lần 1 sinh ra 3 skill nhưng bị hàm `validate_skill` lọc bỏ do tên dùng dấu gạch dưới (`_`, vi phạm regex an toàn `SAFE_NAME`); Lần 2 sau khi tinh chỉnh prompt yêu cầu bắt buộc kebab-case (`-`), curator sinh thành công 3/3 skill hợp lệ.
  - Số skill bị xóa: 0 (tuyệt đối không can thiệp hay sửa tay bất kỳ tệp nào trong `skills/auto/`).

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `prevent-test-modification` | Tổng quát: Áp dụng cho mọi dự án phát triển phần mềm (không sửa test có sẵn, chỉ tạo test mới). | Đúng: Ngăn ngừa triệt để lỗi sửa test để làm pass bài thi thay vì sửa lỗi logic mã nguồn. | 10 dòng (5 dòng checklist), `description`: *"Use this skill to ensure that test files remain unaltered during code modifications."*, `skills_read` = 0. |
| `enforce-type-annotations` | Tổng quát: Áp dụng chuẩn PEP 484 cho toàn bộ hàm public trong package Python. | Đúng: Khớp chính xác với quy ước nội bộ `rule_type_hints` của Acme. | 10 dòng (5 dòng checklist), `description`: *"Use this skill to ensure all public functions have proper type annotations."*, `skills_read` = 0. |
| `validate-csv-formatting` | Bán tổng quát: Áp dụng cho các tác vụ chuẩn hóa dữ liệu bảng/CSV (header, kiểu dữ liệu, timestamp UTC). | Đúng: Nêu rõ quy tắc kiểm tra header, kiểu dữ liệu, UTC ISO-8601 và khử trùng lặp. | 10 dòng (5 dòng checklist), `description`: *"Use this skill to ensure CSV files adhere to specified formatting rules."*, `skills_read` = 0. |

## 7. Kết quả so sánh (Phần 4.3, 4.4)

> Dán nội dung `report/table.md` và kết quả `python scripts/check_breakdown.py`. Nêu các lần chạy có `error` hoặc `skills_modified = true` (nếu có) và cách xử lý.

```text
(dán bảng ở đây)
```

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Bạn đã phòng tránh như thế nào?
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1.
2.
3.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): hướng chọn, kết quả, nhận xét.
- Ghi chú khác:
