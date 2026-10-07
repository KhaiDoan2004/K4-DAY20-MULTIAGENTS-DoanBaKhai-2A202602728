"""GUIDE Phần 3 - Người tuyển chọn skill (skill curator): tự viết skill từ các lần chạy thất bại.   >>> SINH VIÊN CÀI ĐẶT curate_skills <<<

Pseudo-code: guides/pseudocode/04_curator.md
Kiểm tra:    pytest tests/test_04_curator.py
Chạy thật:   python -m lab.curator
"""
import re
from pathlib import Path

import json
from .model import make_model
from .tasks import ROOT, eval_markers   # có sẵn: định danh của tác vụ đánh giá, tính lúc chạy

# ---- CÓ SẴN, KHÔNG SỬA: kiểm tra và tách khối skill (phần dễ sai và liên quan bảo mật) ----------------
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skill(text: str, expected_name: str | None = None) -> list[str]:
    """Kiểm tra nội dung một SKILL.md. Trả về danh sách vấn đề (rỗng = hợp lệ).

    Quy tắc: có khối YAML frontmatter; `name` chữ thường/số/gạch ngang (tối đa 64 ký tự) và bằng `expected_name`
    nếu được truyền; có `description` (tối đa 1024 ký tự); phần thân tối đa 80 dòng; không chứa chuỗi nào của
    `eval_markers()`. Quy tắc về `name` cũng là biện pháp bảo mật: tên khối do LLM sinh ra được dùng để tạo
    đường dẫn, nên `../evil` không được lọt qua.
    """
    problems = []
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text.strip() + "\n", re.S)
    if not m:
        return ["missing YAML frontmatter"]
    front, body = m.groups()
    name = re.search(r"^name:\s*(.+)$", front, re.M)
    desc = re.search(r"^description:\s*(.+)$", front, re.M)
    n = name.group(1).strip() if name else ""
    if not SAFE_NAME.fullmatch(n) or len(n) > 64:
        problems.append("invalid name")
    elif expected_name is not None and n != expected_name:
        problems.append("name differs from the block name")
    if not desc or len(desc.group(1).strip()) > 1024:
        problems.append("missing or too long description")
    if len(body.strip().splitlines()) > 80:
        problems.append("body longer than 80 lines")
    low = text.lower()
    for marker in eval_markers():
        if marker in low:
            problems.append(f"mentions evaluation material: {marker}")
    return problems


def parse_skill_blocks(reply: str) -> list[tuple[str, str]]:
    """Tách câu trả lời của LLM thành danh sách (name, nội dung SKILL.md).

    Khuôn dạng: `=== SKILL: <name> ===` ... `=== END ===`. Một khối kết thúc ở điểm nào đến trước trong ba điểm:
    `=== END ===`, tiêu đề `=== SKILL:` kế tiếp, hoặc cuối văn bản (LLM đôi khi quên dòng END).
    """
    pattern = re.compile(r"^=== SKILL: (\S+) ===[ \t]*\n(.*?)(?=^=== END ===|^=== SKILL: |\Z)", re.S | re.M)
    return [(name, text.strip()) for name, text in pattern.findall(str(reply))]
# --------------------------------------------------------------------------------------------------


def curate_skills(results_dir="results", source_condition="baseline", out_dir=None, model=None, max_skills: int = 3) -> list[Path]:
    """Đọc các lần chạy của TÁC VỤ HỌC (role == "learn") trong `source_condition`, nhờ LLM viết skill, ghi file.

    Các bước: nạp run.json + trace.md -> (nếu không có check nào thất bại: in cảnh báo và trả về [] mà KHÔNG gọi LLM)
    -> dựng prompt -> model.invoke(prompt) -> parse_skill_blocks -> validate_skill(text, expected_name=name)
    -> ghi `<out_dir>/<name>/SKILL.md`. Mặc định `out_dir` = <gốc lab>/skills/auto (dùng `ROOT` từ lab.tasks).
    Giữ tối đa `max_skills` skill hợp lệ; skill không hợp lệ bị bỏ qua.
    Prompt chứa, với mỗi check thất bại, TÊN và trường `detail` (lời nhận xét của bot đánh giá: phát biểu quy tắc bị vi phạm)
    cùng phần cuối của vết (trace). Với tác vụ học, `detail` chỉ phát biểu quy tắc, không chứa đáp án.
    Tuyệt đối KHÔNG đưa dữ liệu của tác vụ đánh giá (role == "eval") vào prompt.
    model mặc định: make_model() (lab.model).
    Trả về: danh sách đường dẫn SKILL.md đã ghi.
    """
    dest = Path(out_dir) if out_dir is not None else (ROOT / "skills" / "auto")

    runs = []
    base_path = Path(results_dir) / source_condition
    if base_path.exists():
        for item in sorted(base_path.iterdir()):
            run_json = item / "run.json"
            if not run_json.is_file():
                continue
            data = json.loads(run_json.read_text(encoding="utf-8"))
            if data.get("role") != "learn":
                continue
            failed = [
                (c.get("name"), c.get("detail", ""))
                for c in data.get("checks", [])
                if not c.get("passed")
            ]
            trace_path = item / "trace.md"
            trace = trace_path.read_text(encoding="utf-8")[-6000:] if trace_path.is_file() else ""
            runs.append({
                "task": data.get("task", item.name),
                "failed": failed,
                "trace": trace,
            })

    if not any(bool(r["failed"]) for r in runs):
        print("Warning: no failed checks found in learning runs.")
        return []

    prompt_parts = [
        "You are an expert engineer authoring high-reusable procedural skills for autonomous coding agents.",
        "Below are failed checks (check names and evaluation bot feedback) and execution traces from prior learning runs.",
        f"Identify common procedural mistakes and write up to {max_skills} concise skills to prevent them on new tasks of similar types.",
        "",
        "Rules for each skill:",
        "- Must be generic: DO NOT mention specific task ids, specific task filenames, or specific numbers.",
        "- CRITICAL: `name` MUST contain ONLY lowercase letters, digits, and single hyphens '-'. NEVER use underscores '_'. MUST be in kebab-case (e.g. prevent-test-modification, enforce-type-annotations, validate-csv-formatting).",
        "- `description` MUST be one sentence: when to use, max 1024 chars.",
        "- Body must be concise instructions / checklist (max 40 lines, never exceed 80 lines).",
        "- Output format exactly for each skill:",
        "=== SKILL: <name> ===",
        "---",
        "name: <name>",
        "description: <when to use this skill>",
        "---",
        "<checklist and guidelines>",
        "=== END ===",
        "",
        "### Learning Runs with Failed Checks:",
    ]
    for r in runs:
        if not r["failed"]:
            continue
        prompt_parts.append(f"\nTask: {r['task']}")
        prompt_parts.append("Failed checks:")
        for fname, fdetail in r["failed"]:
            prompt_parts.append(f"- {fname}: {fdetail}")
        if r["trace"]:
            prompt_parts.append(f"Trace summary:\n{r['trace']}")

    prompt = "\n".join(prompt_parts)
    llm = model or make_model()
    reply = llm.invoke(prompt).content

    written = []
    blocks = parse_skill_blocks(reply)
    for name, text in blocks:
        if len(written) >= max_skills:
            break
        problems = validate_skill(text, expected_name=name)
        if problems:
            continue
        skill_dir = dest / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(text + "\n", encoding="utf-8")
        written.append(skill_file)

    return written


if __name__ == "__main__":
    for p in curate_skills():
        print("wrote", p)
