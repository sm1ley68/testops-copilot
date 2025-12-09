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
                    "max_tokens": 20000,
                }
            )

        if resp.status_code != 200:
            print(f"[RequirementsAgent] LLM API error: {resp.status_code}")
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        print(f"[RequirementsAgent] API response length: {len(content)} characters")

        # Если JSON обрезан - пытаемся восстановить
        if not content.strip().endswith('}') and not content.strip().endswith(']'):
            print(f"[RequirementsAgent] Warning: Response appears truncated, attempting to fix")
            # Добавляем закрывающие скобки если их нет
            if '[' in content and ']' not in content:
                content = content + ']'

        # Парсинг JSON
        try:
            backticks = "```"
            if backticks + "json" in content:
                content = content.split(backticks + "json")[1].split(backticks)[0].strip()
            elif backticks in content:
                parts = content.split(backticks)
                if len(parts) >= 2:
                    content = parts.strip()[1]

            suite_data = json.loads(content)

            # Если LLM вернул массив напрямую
            if isinstance(suite_data, list):
                print(f"[RequirementsAgent] Parsed {len(suite_data)} UI cases from JSON (array format)")
                cases = [TestCase(**case) for case in suite_data]
                return TestSuite(
                    name="Test Suite for UI Calculator",
                    description="Manual test cases for UI testing",
                    cases=cases
                )
            # Если вернул объект с полем cases
            elif isinstance(suite_data, dict):
                print(f"[RequirementsAgent] Parsed {len(suite_data.get('cases', []))} UI cases from JSON (dict format)")
                cases = [TestCase(**case) for case in suite_data.get("cases", [])]
                return TestSuite(
                    name=suite_data.get("name", "Generated Test Suite"),
                    description=suite_data.get("description", ""),
                    cases=cases
                )
            else:
                raise ValueError(f"Unexpected response format: {type(suite_data)}")


        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[RequirementsAgent] Failed to parse LLM response: {e}")
            print(f"[RequirementsAgent] Full content:\n{content}")
            raise Exception(f"Failed to parse LLM response: {e}\nContent: {content[:1000]}")

    async def generate_api_test_cases(self, api_spec: str) -> TestSuite:
        """Генерирует тест-кейсы для API на основе спецификации."""

        system_prompt = """You are a QA automation expert specializing in REST API testing.

        **IMPORTANT: Write ALL content ONLY in ENGLISH.**

        Generate comprehensive manual test cases in Allure TestOps as Code format for the provided API specification.

        Requirements:
        1. Cover all CRUD operations (GET, POST, PATCH, DELETE)
        2. Include authentication testing (Bearer token)
        3. Test both positive and negative scenarios
        4. Verify response status codes and data structure
        5. Test edge cases (invalid IDs, missing parameters, authorization errors)
        6. Use AAA pattern (Arrange-Act-Assert) in steps
        7. Generate at least 15 test cases covering all endpoints

        Return ONLY valid JSON in format:
        {
          "name": "API Test Suite Name",
          "cases": [
            {
              "title": "Clear test case title describing the scenario",
              "description": "Detailed description of what is being tested and why",
              "steps": [
                "Arrange: Prepare authentication token and test data (e.g., valid UUIDv4)",
                "Act: Send HTTP request: METHOD /endpoint with headers and body",
                "Assert: Verify HTTP status code, response structure, and data"
              ],
              "expected_result": "Expected API response status, structure, and behavior",
              "priority": "CRITICAL",
              "tags": ["api", "vms", "positive", "smoke"]
            },
            ...
          ]
        }

        Do NOT add any comments or text before/after JSON."""

        user_prompt = f"""Generate manual test cases for the following API specification:

{api_spec}

Requirements:
- Endpoint base URL: https://compute.api.cloud.ru
- Authentication: Bearer userPlaneApiToken (required in Authorization header)
- ID Format: All IDs must be valid UUIDv4
- Error responses: Return ExceptionSchema format

Generate comprehensive test cases covering:
1. VMs endpoints: GET, POST, PATCH, DELETE operations + start/stop/reboot actions
2. Disks endpoints: CRUD operations + attach/detach to VM
3. Flavors endpoints: GET list and specific flavor details
4. Authentication scenarios: valid token, missing token, invalid token
5. Positive scenarios: valid requests with correct data
6. Negative scenarios: invalid IDs, missing required fields, malformed requests
7. Edge cases: non-existent resources (404), duplicate operations

Minimum 15-20 test cases required."""

        print(f"[RequirementsAgent] Generating API test cases with model: {self._model_name}")

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
                    "max_tokens": 20000,
                }
            )

        if resp.status_code != 200:
            print(f"[RequirementsAgent] API LLM error: {resp.status_code}")
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        content = data["choices"]["message"]["content"]

        print(f"[RequirementsAgent] API response length: {len(content)} characters")

        # Парсинг JSON
        try:
            backticks = "```"
            if backticks + "json" in content:
                content = content.split(backticks + "json")[1].split(backticks)[0].strip()
            elif backticks in content:
                parts = content.split(backticks)
                if len(parts) >= 2:
                    content = parts[1].strip()

            suite_data = json.loads(content)

            print(f"[RequirementsAgent] Parsed API response type: {type(suite_data)}")

            # Если LLM вернул массив напрямую
            if isinstance(suite_data, list):
                cases = [TestCase(**case) for case in suite_data]
                return TestSuite(
                    name="Evolution Compute API Test Suite",
                    description="Manual test cases for VMs, Disks, and Flavors API",
                    cases=cases
                )
            # Если вернул объект с полем cases
            elif isinstance(suite_data, dict):
                cases = [TestCase(**case) for case in suite_data.get("cases", [])]
                return TestSuite(
                    name=suite_data.get("name", "Evolution Compute API Test Suite"),
                    description=suite_data.get("description", "Manual test cases for VMs, Disks, and Flavors API"),
                    cases=cases
                )
            else:
                raise ValueError(f"Unexpected response format: {type(suite_data)}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[RequirementsAgent] Failed to parse API response: {e}")
            print(f"[RequirementsAgent] Full content:\n{content}")
            raise Exception(f"Failed to parse LLM response: {e}\nContent: {content[:1000]}")
