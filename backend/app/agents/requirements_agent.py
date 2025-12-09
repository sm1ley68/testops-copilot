import json
from typing import List
from app.models import TestSuite, TestCase
from app.llm_client import get_llm_client
from app.config import settings


class RequirementsAgent:
    """
    Агент для генерации тест-кейсов из текстовых требований.
    """

    def __init__(self):
        self._model_name = "openai/gpt-oss-120b"

    async def generate_from_requirements_text(self, requirements: str) -> TestSuite:
        """
        Генерирует набор тест-кейсов (минимум 15) для UI калькулятора Cloud.ru.
        """
        system_prompt = """Ты — эксперт по тестированию UI веб-приложений и Allure TestOps.

Твоя задача: на основе требований к функционалу сгенерировать минимум 15 детальных тест-кейсов для ручного тестирования.

Каждый тест-кейс должен содержать:
- title: краткое название теста (например, "Проверка сложения двух положительных чисел")
- description: подробное описание того, что проверяется
- steps: массив шагов в формате AAA (Arrange-Act-Assert):
  * Arrange (подготовка): настройка начального состояния
  * Act (действие): выполнение тестируемого действия
  * Assert (проверка): проверка ожидаемого результата
- expected_result: что должно произойти после выполнения шагов
- priority: "CRITICAL", "HIGH", "NORMAL", или "LOW"
- tags: массив меток для категоризации (например, ["ui", "calculator", "smoke", "regression"])

ВАЖНО:
1. Сгенерируй минимум 15 различных тест-кейсов, покрывающих разные сценарии
2. Включи позитивные и негативные кейсы
3. Покрой edge cases (граничные значения, пустые поля, большие числа)
4. Шаги должны быть чёткими и детальными
5. Используй Allure-теги для группировки: feature, story, severity

Верни ТОЛЬКО валидный JSON в формате:
{
  "name": "Test Suite for UI Calculator",
  "cases": [
    {
      "title": "...",
      "description": "...",
      "steps": ["Arrange: ...", "Act: ...", "Assert: ..."],
      "expected_result": "...",
      "priority": "CRITICAL",
      "tags": ["ui", "calculator", "smoke"]
    },
    ...
  ]
}

НЕ добавляй никаких комментариев или текста до/после JSON."""

        user_prompt = f"""Требования к функционалу UI калькулятора Cloud.ru:

{requirements}

Сгенерируй минимум 15 тест-кейсов для ручного тестирования этого функционала."""

        print(f"[RequirementsAgent] Calling LLM with model: {self._model_name}")

        # Вызов LLM
        with get_llm_client() as client:
            resp = client.post(
                "/chat/completions",
                json={
                    "model": self._model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 13000,
                }
            )

        if resp.status_code != 200:
            print(f"[RequirementsAgent] LLM API error: {resp.status_code}")
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        print(f"[RequirementsAgent] LLM response length: {len(content)} characters")
        print(f"[RequirementsAgent] First 500 chars:\n{content[:500]}")

        # Парсинг JSON
        try:
            # Убираем markdown блоки если есть
            # Убираем markdown блоки если есть
            backticks = "```"
            if backticks + "json" in content:
                content = content.split(backticks + "json").split(backticks).strip()[1]
            elif backticks in content:
                parts = content.split(backticks)
                if len(parts) >= 2:
                    content = parts.strip()[1]

            suite_data = json.loads(content)

            print(f"[RequirementsAgent] Parsed {len(suite_data.get('cases', []))} cases from JSON")

            # Преобразуем в Pydantic модели
            cases = [TestCase(**case) for case in suite_data["cases"]]

            return TestSuite(
                name=suite_data.get("name", "Generated Test Suite"),
                cases=cases
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[RequirementsAgent] Failed to parse LLM response: {e}")
            print(f"[RequirementsAgent] Full content:\n{content}")
            raise Exception(f"Failed to parse LLM response: {e}\nContent: {content[:1000]}")

