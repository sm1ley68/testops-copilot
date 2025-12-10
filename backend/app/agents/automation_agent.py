import json
from typing import List
from app.models import TestSuite, TestCase
from app.llm_client import get_llm_client


class AutomationAgent:
    """
    Агент для генерации автоматизированных pytest тестов из ручных тест-кейсов.
    """

    async def generate_e2e_tests(self, test_suite: TestSuite, base_url: str) -> str:
        system_prompt = """You are an expert in test automation with Python, pytest, and Playwright.

Your task is to generate complete, production-ready pytest E2E test code from manual test cases.

IMPORTANT REQUIREMENTS:
1. Use Playwright for browser automation
2. Follow pytest conventions and best practices
3. Add Allure decorators (@allure.title, @allure.description, @allure.step, @allure.severity)
4. Include proper page object pattern or direct selectors
5. Add clear assertions and error messages
6. Include setup/teardown fixtures
7. Generate ONLY valid Python code, no explanations
8. Use async/await with playwright async API

Output ONLY the Python code, starting with imports."""

        user_prompt = f"""Generate pytest E2E automation tests for the following manual test cases.

Base URL: {base_url}

Test Suite: {test_suite.name}

Test Cases:
{json.dumps([case.dict() for case in test_suite.cases], indent=2, ensure_ascii=False)}

Generate complete pytest code with:
- All necessary imports
- Pytest fixtures for browser setup
- One test function per test case
- Allure decorators matching priority and tags from manual cases
- Clear test steps with allure.step()
- Proper assertions

Return ONLY Python code, no markdown, no explanations."""

        # Вызов LLM (как в requirements_agent)
        with get_llm_client() as client:
            resp = client.post(
                "/chat/completions",
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 8000,
                }
            )

        if resp.status_code != 200:
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        pytest_code = data["choices"][0]["message"]["content"]

        # Убираем markdown форматирование если есть
        if pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("```python", "").replace("```")
        elif pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("```")

        return pytest_code
