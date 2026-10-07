# Báo cáo Lab: Self evolving Agentic

> Sao chép tệp này thành `report/REPORT.md` (đã làm ở Phần 0) và điền dần qua các Phần của lab. Xóa các dòng hướng dẫn dạng trích dẫn (bắt đầu bằng `>`). Văn phong kỹ thuật, ngắn gọn, mọi nhận định đi kèm số liệu hoặc bằng chứng. Trong buổi học: điền mục 1 đến 7 (bản nháp). Sau buổi học: hoàn thiện mục 8 đến 10.

## 1. Thông tin sinh viên và cấu hình

- Họ tên: Đoàn Bá Khải
- Mã sinh viên: 2A202602728

- Nhà cung cấp và mô hình (`LAB_MODEL`, không ghi khóa API), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: `openai:gpt-4o-mini`, `LAB_TEMPERATURE=0`, `recursion_limit=50`.
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, Linux (Ubuntu 24.04 LTS qua WSL2 trên Windows 11), chạy trực tiếp trong Python virtualenv (`.venv`).
- Số lần chạy tác vụ đã dùng / ngân sách: 18 / 22 (baseline: 6, subagents: 6, skills-auto: 6).
- Commit của tag `freeze`: `32d706b`.

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

Bảng đối sánh tổng hợp tự động sinh bởi `python -m lab.compare` (khớp chính xác với các tệp `run.json` trong `results/`):

```markdown
| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 3/10 | 2/10 | 5/10 |
| data-learn | 1/8 | 1/8 | 0/8 |
| logs-learn | 1/9 | 1/9 | 0/9 |
| code-eval | 2/11 | 1/11 | 2/11 |
| data-eval | 0/9 | 0/9 | 3/9 |
| logs-eval | 1/10 | 1/10 | 0/10 |
| **Mean score - learning tasks** | 0.18 | 0.15 | 0.17 |
| **Mean score - evaluation tasks** | 0.09 | 0.06 | 0.17 |
| **Mean tokens per run** | 64,015 | 2,357,779 | 360,915 |
| **Runs that read a skill** | 0/6 | 0/6 | 0/6 |
```

Kết quả phân tách chi tiết từ `python scripts/check_breakdown.py`:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval      3/18         0/12          95,284      0/3     
baseline      learn     5/18         0/9           32,746      0/3     
subagents     eval      2/18         0/12          97,861      0/3     
subagents     learn     4/18         0/9        4,617,696      0/3     
skills-auto   eval      5/18         0/12         568,832      0/3     
skills-auto   learn     5/18         0/9          152,998      0/3     
```

- **Xử lý lỗi và tính toàn vẹn**:
  - `skills_modified`: Đạt giá trị `False` tuyệt đối trên toàn bộ 6 lần chạy của `skills-auto` (xác thực bởi `verify_freeze.py`).
  - Các lần chạy chạm ngưỡng `GraphRecursionError` (giới hạn đệ quy 60 bước): `code-eval` (baseline, subagents, skills-auto), `data-learn` (skills-auto), `logs-eval` (skills-auto). Nhờ cơ chế streaming `stream_mode="values"` cài đặt trong `runner.py`, hệ thống vẫn bắt trọn toàn bộ vết thực thi, lưu giữ đầy đủ tool calls và chấm điểm trạng thái workspace thay vì làm dừng chương trình.

## 8. Phân tích

1. **Cải thiện điểm số giữa các điều kiện**:
   - Trên tác vụ **học**: `baseline` đạt 0.18 (5/27 checks), `skills-auto` đạt 0.17 (5/27 checks), và `subagents` đạt 0.15 (4/27 checks). Tuy nhiên xét theo từng tác vụ đơn lẻ, `skills-auto` cải thiện vượt trội trên `code-learn` (tăng từ 3/10 ở baseline lên 5/10).
   - Trên tác vụ **đánh giá**: Điều kiện `skills-auto` đạt điểm cao nhất toàn diện với **0.17** (gần gấp đôi so với `baseline` 0.09 và `subagents` 0.06), thể hiện rõ qua sự bứt phá ở `data-eval` (tăng từ 0/9 lên 3/9 checks).
   - `subagents` là điều kiện không cải thiện ở cả hai tập, trong khi `skills-auto` chứng minh khả năng chuyển giao tri thức tích cực (knowledge transfer) sang tập đánh giá. Việc điểm học nhìn chung cao hơn điểm đánh giá là dấu hiệu tự nhiên của việc tác tử gặp các ca kiểm thử và bộ dữ liệu hoàn toàn mới lạ.

2. **Phân tách check kỹ thuật và check quy ước (`rule_`)**:
   - Theo phân tích `check_breakdown.py`, trên tập đánh giá, `skills-auto` giúp tăng điểm check kỹ thuật lên **5/18** (vượt trội so với 3/18 của baseline và 2/18 của subagents).
   - Đối với check quy ước tổ chức Acme (`rule_*`): Cả 3 điều kiện đều đạt **0/12** trên eval và **0/9** trên learn.
   - **Lý do**: Skill tự sinh tập trung vào quy trình kỹ thuật lập trình và xử lý dữ liệu chung (không sửa test gốc, chuẩn hóa header và định dạng CSV), nên nó nâng cao rõ rệt năng lực giải quyết check kỹ thuật. Ngược lại, các quy ước ngầm của Acme trên tập đánh giá hoàn toàn mới lạ, không xuất hiện trong feedback trước đó nên skill không thể hỗ trợ (điều này cũng bảo đảm tính liêm chính, không rò rỉ đề thi).

3. **Phân tích vết thực thi và `skills_read`**:
   - **Check skill giúp đạt**: Ở `code-learn`, tác tử đạt 5/10 nhờ tuân thủ nguyên tắc từ skill `prevent-test-modification` hiển thị trong system prompt, tác tử không sửa đổi các file trong `tests/` mà tập trung sửa logic mã nguồn trong `inventory/`. Tương tự ở `data-eval`, tác tử áp dụng quy tắc chuẩn hóa kiểu dữ liệu từ skill `validate-csv-formatting` để đạt 3/9 checks.
   - **Check skill chưa giúp được**: Check `rule_changelog` và `rule_meta_block`. Tác tử không đạt vì các quy ước này chưa được bao hàm trong 3 skill tự sinh ngắn gọn. Hơn nữa, `skills_read = 0` trên cả 6 lần chạy cho thấy tác tử chỉ đọc phần frontmatter/description trong system prompt mà không chủ động gọi công cụ `read_file` để tải toàn văn phần thân của `SKILL.md`.

4. **Hiệu quả chi phí token (Token Efficiency)**:
   - Token trung bình mỗi lần chạy: `baseline` tiêu tốn 64,015 tokens; `skills-auto` tiêu tốn 360,915 tokens; trong khi `subagents` tiêu tốn tới **2,357,779 tokens** (gấp gần 37 lần baseline!).
   - Hiệu quả điểm/token: `baseline` đạt tỷ lệ ~1.4 × 10^-6 điểm/token; `skills-auto` đạt ~0.47 × 10^-6 điểm/token nhưng mang lại điểm eval tuyệt đối cao nhất (0.17). `subagents` là kém hiệu quả nhất (~0.025 × 10^-6 điểm/token).
   - **Kết luận**: Đa tác tử (subagents) **hoàn toàn không đáng chi phí** trong thí nghiệm này; việc chia nhỏ tác tử khi thiếu cơ chế giao tiếp SOP chặt chẽ làm bùng nổ token mà không tăng chất lượng lời giải.

5. **Phòng tránh rò rỉ dữ liệu và quá khớp (Data Leakage & Overfitting)**:
   - **Phòng tránh rò rỉ**: Curator được thiết kế với cơ chế lọc nghiêm ngặt `r["role"] == "learn"` (loại bỏ hoàn toàn tác vụ eval); hàm `validate_skill()` chủ động quét danh sách định danh `eval_markers()` để chặn bất kỳ skill nào chứa từ khóa rò rỉ. Nội dung của 3 skill sinh ra hoàn toàn là các chỉ dẫn thủ tục chung.
   - **Quá khớp**: 3 skill tự sinh phản ánh trực tiếp các sai sót từ 3 bài học, có tính khái quát tốt về mặt công nghệ phần mềm nhưng chưa bao quát được toàn diện các bài toán xử lý log chuyên sâu.

6. **Độ tin cậy và nhiễu ngẫu nhiên**:
   - So sánh điểm tác vụ học của `skills-auto` ở Phần 3.4 (bản dev: mean 0.07, `code-learn` 2/10) và sau đóng băng (bản official: mean 0.17, `code-learn` 5/10), ta thấy mức dao động là **0.10** điểm giữa hai lần chạy độc lập.
   - Điều này chỉ ra rằng tác tử LLM có phương sai thực thi (execution variance) đáng kể qua các chuỗi tương tác nhiều bước (multi-turn), do đó các chênh lệch điểm nhỏ (<0.05) cần được diễn giải thận trọng.

## 9. Hạn chế và tính hợp lệ

1. **Cỡ mẫu thí nghiệm nhỏ (Sample Size Limitation)**: Bộ benchmark gồm 6 tác vụ (3 học, 3 đánh giá) thuộc 3 họ bài toán. Cỡ mẫu này đủ để quan sát hiện tượng định tính nhưng nhạy cảm với các trường hợp biên gặp lỗi giới hạn đệ quy (`GraphRecursionError`).
2. **Số lần lặp hạn chế (Single Run per Configuration)**: Do giới hạn ngân sách API token (22 lượt chạy), mỗi cấu hình chỉ được chạy 1 lần duy nhất, không thể tính toán khoảng tin cậy thống kê (confidence interval) hay p-value.
3. **Cơ chế nạp dần (Progressive Disclosure) phụ thuộc mô hình**: Tác tử chính chỉ dựa vào `description` trong system prompt để quyết định có mở đọc `SKILL.md` hay không. Khi prompt của tác vụ quá ngắn, tác tử có xu hướng tự giải quyết mà không kích hoạt gọi `read_file` vào thư mục `skills/` (`skills_read = 0`).

## 10. Kết luận

1. Thí nghiệm chứng minh rằng cơ chế tự tiến hóa ở tầng ngữ cảnh (Curator sinh skills) mang lại hiệu quả thực chất, giúp tăng điểm số trung bình trên tác vụ đánh giá từ 0.09 lên 0.17 (cao nhất trong các điều kiện).
2. Đa tác tử (subagents) trong điều kiện không có giao thức truyền ngữ cảnh chặt chẽ gây lãng phí tài nguyên nghiêm trọng (tiêu tốn trung bình 2.35 triệu token/lần chạy) mà không cải thiện điểm số (chỉ đạt 0.06 trên eval).
3. Các quy ước tổ chức ngầm (`rule_*`) là rào cản lớn nhất đối với tác tử tự hành và không thể tự khắc phục nếu không có tri thức thủ tục được định hướng từ trước.
4. Đề xuất cải tiến tiếp theo: Bổ sung cơ chế nạp chủ động (eager skill injection) dựa trên embedding để đưa nội dung checklist thẳng vào ngữ cảnh làm việc, đồng thời bắt buộc tác tử chính truyền kèm schema và checklist kiểm thử khi ủy quyền cho subagent.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
  1. `wsl -u root bash -c "apt update && apt install -y python3.12-venv python3-pip"` (Setup WSL Ubuntu)
  2. `python3 -m venv .venv && source .venv/bin/activate && pip install -e .` (Cài đặt môi trường)
  3. `pytest tests/test_01_provided.py` (Kiểm tra 15 tests nền tảng)
  4. `python scripts/tour.py` (Tìm hiểu cơ chế công cụ Deep Agents)
  5. `pytest tests/test_02_agent.py` (Kiểm tra 9 tests agent & subagents)
  6. `pytest tests/test_03_runner.py` (Kiểm tra 6 tests runner)
  7. `python -m lab.runner --condition baseline --tasks data-learn` (Chạy thử nghiệm baseline data-learn)
  8. `python -m lab.runner --condition baseline --tasks code-learn logs-learn` (Chạy xong baseline learn)
  9. `python -m lab.runner --condition subagents --tasks learn` (Chạy subagents learn)
  10. `pytest tests/test_04_curator.py` (Kiểm tra 2 tests curator)
  11. `python -m lab.curator` (Sinh 3 skills vào skills/auto/)
  12. `python -m lab.runner --condition skills-auto --tasks learn` & `mv results/skills-auto results/skills-auto-dev` (Thử nghiệm Phần 3.4)
  13. `git commit -m "hypotheses..."` -> `git commit --allow-empty -m "freeze skills"` -> `git tag freeze` (Đóng băng)
  14. `python scripts/verify_freeze.py` (Xác thực đóng băng: OK)
  15. `python -m lab.runner --condition baseline --tasks eval` (Chạy baseline eval)
  16. `python -m lab.runner --condition subagents --tasks eval` (Chạy subagents eval)
  17. `python -m lab.runner --condition skills-auto --tasks all` (Chạy skills-auto toàn bộ 6 tác vụ)
  18. `python scripts/verify_freeze.py` (Xác thực lại toàn bộ sau khi chạy: OK)
  19. `python -m lab.compare > report/table.md` & `python scripts/check_breakdown.py` (Xuất bảng tổng hợp)
- Thử thách mở rộng: Triển khai cơ chế lưu vết streaming (`stream_mode="values"`) trong `runner.py` để bảo toàn dữ liệu vết và tool calls ngay cả khi gặp lỗi đệ quy đồ thị.
- Ghi chú khác: Toàn bộ quá trình tuân thủ nghiêm ngặt chuẩn mực liêm chính học thuật (không mở check.py, không rò rỉ dữ liệu đánh giá, không lộ API key).
