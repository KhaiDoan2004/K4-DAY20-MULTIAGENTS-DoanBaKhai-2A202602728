"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {
            "name": "explorer",
            "description": (
                "Use when you need to inspect existing workspace files, understand requirements from "
                "README or docstrings, explore codebase structure, profile data, or inspect error logs. "
                "This agent examines files and reports findings without making any modifications."
            ),
            "system_prompt": (
                "You are an exploratory analysis subagent. Your role is to read files, examine directory structures, "
                "inspect logs, and profile data according to the instructions given by the main agent. "
                "Never modify, create, or delete any files. Report your factual findings, schema details, conventions, "
                "and error traces concisely and accurately back to the main agent."
            ),
        },
        {
            "name": "reviewer",
            "description": (
                "Use when you need an independent verification of task results, edge cases, output formatting, "
                "or compliance against the specification before completing the task. "
                "This agent inspects results without modifying files."
            ),
            "system_prompt": (
                "You are an independent review and quality assurance subagent. Your role is to rigorously check "
                "whether the solution produced in the workspace strictly satisfies all instructions, constraints, "
                "and edge cases specified in the task. Review files and report any discrepancies, formatting issues, "
                "or regressions. Do not make code or file modifications yourself; provide clear, actionable feedback."
            ),
        },
        {
            "name": "implementer",
            "description": (
                "Use when executing focused coding, refactoring, data transformation, or bug fixing steps "
                "that require creating or modifying files and running tests to verify the fix."
            ),
            "system_prompt": (
                "You are an implementation subagent. Your role is to perform specific coding, data processing, "
                "or bug fix tasks requested by the main agent. Follow all workspace conventions, implement the minimal "
                "necessary changes cleanly, and run tests via shell execute to verify your changes. Report what you modified "
                "and the test outcomes back to the main agent."
            ),
        },
    ]
