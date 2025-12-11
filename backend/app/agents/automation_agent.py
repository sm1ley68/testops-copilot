import json
from typing import List
from app.models import TestSuite, TestCase
from app.llm_client import get_llm_client


class AutomationAgent:
    """
    Агент для генерации автоматизированных pytest тестов из ручных тест-кейсов.
    """

    async def generate_from_swagger(self, swagger_data: dict, base_url: str) -> str:
        """
        Генерирует pytest API тесты из реального Swagger/OpenAPI JSON.
        Парсит все эндпоинты и создаёт тест для каждого.
        """

        paths = swagger_data.get('paths', {})

        system_prompt = """You are an expert in API test automation with Python, pytest, httpx, and Allure.

Your task is to generate complete, production-ready pytest API tests from OpenAPI/Swagger specification.

IMPORTANT REQUIREMENTS:
1. Use httpx.Client for HTTP requests
2. Generate ONE test function for EACH endpoint from the specification
3. Add Allure decorators (@allure.title, @allure.description, @allure.step, @allure.severity, @allure.tag)
4. Include proper request/response validation based on spec
5. Validate status codes, response schemas, headers
6. Include pytest fixture for api_client setup
7. Generate ONLY valid Python code, no explanations or markdown
8. Test both success and error cases where applicable
9. Use parameters from spec (path, query, body)
10. Follow AAA pattern (Arrange-Act-Assert)

Output ONLY the Python code, starting with imports."""

        user_prompt = f"""Generate pytest API automation tests from this Swagger/OpenAPI specification.

Base URL: {base_url}

API Specification (paths and methods):
{json.dumps(paths, indent=2, ensure_ascii=False)}

Generate complete pytest code with:
- All necessary imports (pytest, httpx, allure, json)
- Pytest fixture api_client with base_url
- ONE test function per endpoint/method combination
- Use actual endpoint paths, methods, parameters from spec
- Allure decorators for each test
- Clear test steps with allure.step()
- Assertions for status codes and response structure
- Handle authentication if specified in spec

CRITICAL: Generate tests for ALL endpoints in the specification, not just examples.

Return ONLY Python code, no markdown blocks, no explanations."""

        with get_llm_client() as client:
            resp = client.post(
                "/chat/completions",
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,  # Низкая температура для точности
                    "max_tokens": 16000,  # Больше токенов для всех эндпоинтов
                }
            )

        if resp.status_code != 200:
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        pytest_code = data["choices"][0]["message"]["content"]

        # Убираем markdown если есть
        if "```":
            pytest_code = pytest_code.split("```python").split("```")
        elif "```" in pytest_code:
            pytest_code = pytest_code.replace("```")

        return pytest_code.strip()

    async def generate_e2e_tests(self, test_suite: TestSuite, base_url: str) -> str:
        """
        Генерирует pytest E2E тесты с Playwright из ручных тест-кейсов.
        """
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

        # Вызов LLM
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

        if pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("``````", "")
        elif pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("```", "")

        return pytest_code

    async def generate_api_tests(self, test_suite: TestSuite, base_url: str) -> str:

        system_prompt = """You are an expert in API test automation with Python, pytest, and httpx/requests.

Your task is to generate complete, production-ready pytest API test code from manual test cases.

IMPORTANT REQUIREMENTS:
1. Use httpx or requests for HTTP requests
2. Follow pytest conventions and best practices
3. Add Allure decorators (@allure.title, @allure.description, @allure.step, @allure.severity)
4. Include proper request/response validation
5. Add clear assertions for status codes, response body, headers
6. Include setup/teardown fixtures for authentication if needed
7. Generate ONLY valid Python code, no explanations
8. Test error cases and edge cases mentioned in test cases

Output ONLY the Python code, starting with imports."""

        user_prompt = f"""Generate pytest API automation tests for the following manual test cases.

Base API URL: {base_url}

Test Suite: {test_suite.name}

Test Cases:
{json.dumps([case.dict() for case in test_suite.cases], indent=2, ensure_ascii=False)}

Generate complete pytest code with:
- All necessary imports (pytest, httpx, allure, json)
- Pytest fixtures for API client setup
- One test function per test case
- Allure decorators matching priority and tags from manual cases
- Clear test steps with allure.step()
- Proper assertions for status codes, response bodies, headers
- Error handling and validation

Return ONLY Python code, no markdown, no explanations."""

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

        if pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("```", "").strip()
        elif pytest_code.startswith("```"):
            pytest_code = pytest_code.replace("```", "").strip()

        return pytest_code
