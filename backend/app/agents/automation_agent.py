from app.models import TestSuite, AutomatedTest


class AutomationAgent:
    """
    Агент, который переводит TestSuite в набор e2e-тестов.
    Пока заглушка: один файл с комментариями.
    """

    async def generate_from_suite(self, suite: TestSuite) -> list[AutomatedTest]:
        code_lines: list[str] = [
            "import pytest",
            "",
            "",
            "class TestGeneratedE2E:",
        ]

        for idx, case in enumerate(suite.cases, start=1):
            fn_name = f"test_case_{idx}"
            code_lines.append(f"    def {fn_name}(self):")
            code_lines.append(f"        # {case.title}")
            for step in case.steps:
                code_lines.append(f"        # STEP: {step}")
            code_lines.append(f"        # EXPECT: {case.expected_result}")
            code_lines.append("")

        code = "\n".join(code_lines)

        return [
            AutomatedTest(
                kind="ui_e2e",
                path="tests/test_generated_e2e.py",
                code=code,
            )
        ]
