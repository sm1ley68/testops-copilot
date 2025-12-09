from app.models import TestSuite, ValidationReport, ValidationIssue
from app.llm_client import get_llm_client


class ValidationAgent:
    def __init__(self, model_name: str = "zai-org/GLM-4.6"):
        self._model_name = model_name

    async def validate_test_suite(self, suite: TestSuite) -> ValidationReport:
        """
        Валидирует TestSuite через LLM и возвращает ValidationReport.
        """
        system_prompt = (
            "Ты эксперт по тестированию и стандартам Allure TestOps as Code.\n"
            "Твоя задача — проверить набор тест-кейсов на соответствие стандартам:\n\n"
            "1. **Структура**: у каждого кейса должны быть:\n"
            "   - title (название)\n"
            "   - description (описание)\n"
            "   - steps (список шагов, минимум 1)\n"
            "   - expected_result (ожидаемый результат)\n"
            "   - priority (CRITICAL, NORMAL или LOW)\n"
            "   - tags (список тегов)\n\n"
            "2. **Паттерн AAA** (Arrange-Act-Assert):\n"
            "   - Шаги должны явно разделяться на подготовку (Arrange), действие (Act), проверку (Assert).\n"
            "   - Если структура AAA не прослеживается — это warning.\n\n"
            "3. **Allure-декораторы** (для Python-кода):\n"
            "   - Должны быть @allure.feature, @allure.story, @allure.title\n"
            "   - @allure.tag для критичности\n"
            "   - @allure.label('priority', ...) или аналог\n"
            "   - Если декораторы отсутствуют или неполные — это critical/warning.\n\n"
            "4. **Полнота меток**: owner, suite, jira-ссылка (если применимо).\n\n"
            "Верни результат **строго в формате JSON** ValidationReport:\n"
            "{\n"
            '  "total_cases": <int>,\n'
            '  "passed": <int>,\n'
            '  "failed": <int>,\n'
            '  "issues": [\n'
            "    {\n"
            '      "test_case_id": "<id или номер кейса>",\n'
            '      "test_case_title": "<название кейса>",\n'
            '      "severity": "critical" | "warning" | "info",\n'
            '      "issue": "<описание проблемы>",\n'
            '      "recommendation": "<рекомендация по исправлению>"\n'
            "    }\n"
            "  ],\n"
            '  "summary": "<общий итог проверки>"\n'
            "}\n\n"
            "Не добавляй лишний текст вне JSON."
        )

        suite_json = suite.model_dump_json(indent=2, ensure_ascii=False)

        user_prompt = (
            "Проверь следующий набор тест-кейсов на соответствие стандартам:\n\n"
            f"{suite_json}\n\n"
            "Верни ValidationReport в формате JSON."
        )

        payload = {
            "model": self._model_name,
            "max_tokens": 2500,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        with get_llm_client() as client:
            resp = client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]

        try:
            report = ValidationReport.model_validate_json(content)
        except Exception as e:
            report = ValidationReport(
                total_cases=len(suite.cases),
                passed=0,
                failed=len(suite.cases),
                issues=[
                    ValidationIssue(
                        test_case_id="parse_error",
                        test_case_title="LLM Response Parse Error",
                        severity="critical",
                        issue=f"Не удалось распарсить ответ LLM как JSON: {str(e)}",
                        recommendation=f"Ответ LLM: {content[:300]}",
                    )
                ],
                summary="Ошибка парсинга ответа от LLM",
            )

        return report
