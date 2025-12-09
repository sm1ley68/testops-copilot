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
        system_prompt = """You are an expert in UI web application testing and Allure TestOps.

        **IMPORTANT: Write ALL content ONLY in ENGLISH. Do NOT use Russian or any other language.**

        Your task: based on functional requirements, generate at least 15 detailed manual test cases.

        Each test case must contain:
        - title: brief test name (e.g., "Verify addition of two positive numbers")
        - description: detailed description of what is being tested
        - steps: array of steps in AAA format (Arrange-Act-Assert):
          * Arrange: set up initial state
          * Act: perform tested action
          * Assert: verify expected result
        - expected_result: what should happen after executing steps
        - priority: "CRITICAL", "HIGH", "NORMAL", or "LOW"
        - tags: array of labels for categorization (e.g., ["ui", "calculator", "smoke", "regression"])

        CRITICAL REQUIREMENTS:
        1. Generate at least 15 different test cases covering various scenarios
        2. Include positive and negative test cases
        3. Cover edge cases (boundary values, empty fields, large numbers)
        4. Steps must be clear and detailed
        5. Use Allure tags for grouping: feature, story, severity

        Return ONLY valid JSON in format:
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
        
        Example of a well-structured test case:
        {
          "title": "Verify division by zero error handling",
          "description": "Test that calculator displays error message when user attempts to divide by zero",
          "steps": [
            "Arrange: Open calculator application",
            "Act: Enter '5', press '/', enter '0', press '='",
            "Assert: Error message 'Division by zero is not allowed' is displayed"
          ],
          "expected_result": "Error message shown, calculator remains functional",
          "priority": "CRITICAL",
          "tags": ["ui", "calculator", "negative", "error-handling"]
        }
        
        Do NOT add any comments or text before/after JSON."""

        user_prompt = f"""Functional requirements for Cloud.ru UI calculator:

        {requirements}

        Generate at least 15 test cases for manual testing of this functionality."""

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
                    "temperature": 0.8,
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

