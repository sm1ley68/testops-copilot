from typing import List
from app.models import TestSuite, TestCase


class AllureCodeGenerator:
    """
    Генерирует Python код в формате Allure TestOps as Code из TestSuite.
    """

    def generate_allure_code(self, test_suite: TestSuite, owner: str = "qa_team") -> str:
        """
        Преобразует TestSuite в Python код с Allure декораторами.
        """
        class_name = self._generate_class_name(test_suite.name)

        code_lines = [
            "import allure",
            "from allure_commons._allure import step as allure_step",
            "from pytest import mark",
            "",
            "",
            f"@allure.manual",
            f"@allure.label('owner', '{owner}')",
            f"@allure.feature('{test_suite.name}')",
            f"@allure.suite('manual')",
            f"@mark.manual",
            f"class {class_name}:",
            ""
        ]

        # Генерируем методы для каждого тест-кейса
        for case in test_suite.cases:
            test_method = self._generate_test_method(case)
            code_lines.extend(test_method)
            code_lines.append("")

        return "\n".join(code_lines)

    def _generate_class_name(self, suite_name: str) -> str:
        """Генерирует имя класса из названия сьюта."""
        # Убираем спецсимволы и делаем CamelCase
        words = suite_name.replace("-", " ").replace("_", " ").split()
        class_name = "".join(word.capitalize() for word in words)
        if not class_name.endswith("Tests"):
            class_name += "Tests"
        return class_name

    def _generate_test_method(self, case: TestCase) -> List[str]:
        """Генерирует один тест-метод из TestCase."""
        method_name = self._generate_method_name(case.title)

        lines = [
            f"    @allure.title('{self._escape_string(case.title)}')",
            f"    @allure.description('{self._escape_string(case.description)}')",
        ]

        # Добавляем теги
        for tag in case.tags:
            lines.append(f"    @allure.tag('{tag}')")

        # Добавляем приоритет
        lines.append(f"    @allure.label('priority', '{case.priority}')")

        # Генерируем метод
        lines.extend([
            f"    def {method_name}(self) -> None:",
            f"        \"\"\"",
            f"        {self._escape_string(case.description)}",
            f"        ",
            f"        Expected: {self._escape_string(case.expected_result)}",
            f"        \"\"\"",
        ])

        # Добавляем шаги
        for i, step in enumerate(case.steps, 1):
            step_text = self._escape_string(step)
            lines.append(f"        with allure_step('{step_text}'):")
            lines.append(f"            pass")

        return lines

    def _generate_method_name(self, title: str) -> str:
        """Генерирует имя метода из заголовка."""
        # Убираем спецсимволы, делаем snake_case
        clean = title.lower()
        for char in ".,;:!?()[]{}\"'":
            clean = clean.replace(char, "")
        words = clean.split()
        method_name = "test_" + "_".join(words[:8])  # Ограничиваем длину
        return method_name

    def _escape_string(self, text: str) -> str:
        """Экранирует спецсимволы для Python строк."""
        return text.replace("'", "\\'").replace("\n", "\\n")
