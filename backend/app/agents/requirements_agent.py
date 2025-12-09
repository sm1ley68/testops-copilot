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
        self._model_name = "gpt-oss-120b"

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
                    "temperature": 0.7,  # немного креативности для разнообразия кейсов
                    "max_tokens": 4000,  # достаточно для 15+ кейсов
                }
            )

        if resp.status_code != 200:
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Парсинг JSON
        try:
            # Иногда LLM добавляет markdown блоки ``````
            if "```
                content = content.split("```json").split("```
                elif "```" in content:
                content = content.split("``````")[0].strip()

                suite_data = json.loads(content)

                # Преобразуем в Pydantic модели
                cases = [TestCase(**case) for case in suite_data["cases"]]

            return TestSuite(
                name=suite_data.get("name", "Generated Test Suite"),
                cases=cases
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise Exception(f"Failed to parse LLM response: {e}\nContent: {content}")
