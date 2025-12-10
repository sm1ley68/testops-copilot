import json
from typing import List, Optional
import httpx
import yaml
import re
from app.models import TestSuite, TestCase
from app.llm_client import get_llm_client
from app.config import settings
from app.models import UiModel


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
                content = content.split(backticks + "json").split(backticks).strip()[1]
            elif backticks in content:
                parts = content.split(backticks)
                if len(parts) >= 2:
                    content = parts.strip()[1]

            suite_data = json.loads(content)

            # Если LLM вернул массив напрямую
            if isinstance(suite_data, list):
                for case in suite_data:
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
                print(f"[RequirementsAgent] Parsed {len(suite_data)} UI cases from JSON (array format)")
                cases = [TestCase(**case) for case in suite_data]
                return TestSuite(
                    name="Test Suite for UI Calculator",
                    description="Manual test cases for UI testing",
                    cases=cases
                )
            # Если вернул объект с полем cases
            elif isinstance(suite_data, dict):
                for case in suite_data.get("cases", []):
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
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

    async def generate_api_test_cases(self, api_spec: str, requirements_text: Optional[str] = None) -> TestSuite:
        """Генерирует тест-кейсы для API на основе текстовой спецификации."""

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
        7. Generate exactly 15 ultra-concise test cases. Requirements:
    - Each test case description: maximum 50 words
    - Steps: maximum 3 steps, each under 20 words
    - Expected result: maximum 30 words
    - Use brief, direct language without extra explanations

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

Additional requirements:
{requirements_text or 'Generate comprehensive test cases covering all endpoints, authentication, positive/negative scenarios, and edge cases.'}

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
                    "temperature": 0.7,
                    "max_tokens": 50000,
                }
            )

        if resp.status_code != 200:
            print(f"[RequirementsAgent] LLM API error: {resp.status_code}")
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
                for case in suite_data:
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
                cases = [TestCase(**case) for case in suite_data]
                return TestSuite(
                    name="Evolution Compute API Test Suite",
                    description="Manual test cases for VMs, Disks, and Flavors API",
                    cases=cases
                )
            # Если вернул объект с полем cases
            elif isinstance(suite_data, dict):
                for case in suite_data.get("cases", []):
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
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

    async def generate_from_api_spec(
            self,
            swagger_url: Optional[str] = None,
            swagger_text: Optional[str] = None,
            requirements_text: Optional[str] = None
    ) -> TestSuite:
        """
        Генерирует тест-кейсы из OpenAPI/Swagger спецификации.
        Принимает либо URL на swagger.json/yaml, либо текст спецификации.
        """
        print(f"[RequirementsAgent] generate_from_api_spec called")
        print(f"[RequirementsAgent] Raw swagger_url={repr(swagger_url)}, has_text={bool(swagger_text)}")

        # ✅ Извлекаем и очищаем URL
        if swagger_url:
            # Убираем markdown форматирование типа [text](url)
            if '](http' in swagger_url:
                # Markdown link: [text](url)
                match = re.search(r'\]\((https?://[^\)]+)\)', swagger_url)
                if match:
                    swagger_url = match.group(1)

            # Извлекаем URL из текста
            url_pattern = r'(https?://[^\s\[\]\(\)]+)'
            matches = re.findall(url_pattern, swagger_url)
            if matches:
                swagger_url = matches[0].strip()
                print(f"[RequirementsAgent] Extracted URL from text: {swagger_url}")

            # Убираем непечатаемые символы и пробелы
            swagger_url = ''.join(char for char in swagger_url if char.isprintable() and not char.isspace())
            print(f"[RequirementsAgent] Final cleaned URL: {swagger_url}")

        # 1. Получаем спецификацию
        spec_content = ""

        if swagger_url:
            print(f"[RequirementsAgent] Fetching spec from URL: {swagger_url}")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                try:
                    response = await client.get(swagger_url)
                    response.raise_for_status()
                    spec_content = response.text
                    print(f"[RequirementsAgent] Fetched {len(spec_content)} bytes")
                except httpx.InvalidURL as e:
                    print(f"[RequirementsAgent] Invalid URL error: {e}")
                    print(f"[RequirementsAgent] URL bytes: {swagger_url.encode('utf-8')}")
                    raise Exception(
                        f"Invalid Swagger URL format. Please provide a clean URL like: https://petstore3.swagger.io/api/v3/openapi.json")
                except httpx.HTTPStatusError as e:
                    raise Exception(f"Failed to fetch Swagger from URL: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    raise Exception(f"Failed to fetch Swagger from URL: {str(e)}")
        elif swagger_text:
            spec_content = swagger_text
            print(f"[RequirementsAgent] Using provided spec text: {len(spec_content)} bytes")
        else:
            raise ValueError("Either swagger_url or swagger_text must be provided")

        # 2. Парсим спецификацию (JSON или YAML)
        try:
            spec_dict = json.loads(spec_content)
            print("[RequirementsAgent] Parsed as JSON")
        except json.JSONDecodeError:
            try:
                spec_dict = yaml.safe_load(spec_content)
                print("[RequirementsAgent] Parsed as YAML")
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid OpenAPI spec format: {e}")

        # 3. Извлекаем базовую информацию
        api_title = spec_dict.get("info", {}).get("title", "API")
        api_version = spec_dict.get("info", {}).get("version", "1.0.0")
        base_url = ""
        if "servers" in spec_dict and spec_dict["servers"]:
            base_url = spec_dict["servers"][0].get("url", "")

        print(f"[RequirementsAgent] API: {api_title} v{api_version}, base_url={base_url}")

        # 4. Извлекаем эндпоинты
        endpoints_summary = self._extract_endpoints_summary(spec_dict)
        print(f"[RequirementsAgent] Extracted {len(endpoints_summary)} endpoints")

        # 5. Формируем промпт для LLM
        system_prompt = f"""You are a QA automation expert specializing in REST API testing.

**IMPORTANT: Write ALL content ONLY in ENGLISH.**

Generate comprehensive manual test cases for REST API based on OpenAPI specification.

Requirements:
- Generate 15-25 test cases covering all major endpoints
- Include positive scenarios (happy path)
- Include negative scenarios (invalid data, missing auth, not found, conflicts)
- Test authentication and authorization
- Test data validation and error handling
- Cover edge cases (empty lists, invalid IDs, boundary values)
- Use AAA pattern (Arrange-Act-Assert) in steps
- Each test case must have:
  * title: Clear descriptive name
  * description: What is being tested and why (max 50 words)
  * steps: Detailed API call steps (max 3 steps, each under 20 words)
  * expected_result: Expected HTTP status code and response format (max 30 words)
  * priority: CRITICAL (auth, core CRUD), HIGH (important flows), NORMAL (standard), LOW (edge cases)
  * tags: ["api", endpoint category, scenario type]

API Base URL: {base_url}
API Title: {api_title}

Return ONLY valid JSON (no markdown, no explanations):
{{
  "name": "Test Suite Name",
  "cases": [
    {{
      "title": "Test case title",
      "description": "What is tested",
      "steps": ["Arrange: ...", "Act: ...", "Assert: ..."],
      "expected_result": "Expected outcome",
      "priority": "HIGH",
      "tags": ["api", "tag"]
    }}
  ]
}}
"""

        user_prompt = f"""OpenAPI Specification Summary:

API: {api_title} v{api_version}
Base URL: {base_url}

Endpoints:
{json.dumps(endpoints_summary[:20], indent=2)}

Additional Requirements:
{requirements_text or 'Generate comprehensive test cases covering all endpoints with CRUD operations, authentication, positive/negative scenarios, and edge cases.'}

Generate 15-25 API test cases.
"""

        print("[RequirementsAgent] Calling LLM for API spec generation...")

        # 6. Вызываем LLM
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
                    "max_tokens": 50000,
                }
            )

        if resp.status_code != 200:
            print(f"[RequirementsAgent] LLM API error: {resp.status_code}")
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        print(f"[RequirementsAgent] LLM response length: {len(content)} characters")

        try:
            backticks = "```"
            if backticks + "json" in content:
                content = content.split(backticks + "json")[1].split(backticks).strip()
            elif backticks in content:
                parts = content.split(backticks)
                if len(parts) >= 2:
                    content = parts[1].strip()

            suite_data = json.loads(content.strip())
            print(f"[RequirementsAgent] Parsed response type: {type(suite_data)}")

            # Если LLM вернул массив напрямую
            if isinstance(suite_data, list):
                for case in suite_data:
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
                cases = [TestCase(**case) for case in suite_data]
                return TestSuite(
                    name=f"{api_title} API Test Suite",
                    description=f"Manual test cases for {api_title} v{api_version}",
                    cases=cases
                )
            # Если вернул объект с полем cases
            elif isinstance(suite_data, dict):
                for case in suite_data.get("cases", []):
                    if isinstance(case, dict):
                        priority = str(case.get("priority", "NORMAL")).upper().strip()
                        if priority not in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"]:
                            priority = "NORMAL"
                        case["priority"] = priority
                cases = [TestCase(**case) for case in suite_data.get("cases", [])]
                return TestSuite(
                    name=suite_data.get("name", f"{api_title} API Test Suite"),
                    description=suite_data.get("description", f"Manual test cases for {api_title} v{api_version}"),
                    cases=cases
                )
            else:
                raise ValueError(f"Unexpected response format: {type(suite_data)}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[RequirementsAgent] Failed to parse LLM response: {e}")
            print(f"[RequirementsAgent] Full content:\n{content[:500]}")
            raise Exception(f"Failed to parse LLM response: {e}")

    def _extract_endpoints_summary(self, spec_dict: dict) -> list:
        """
        Извлекает краткую информацию об эндпоинтах из OpenAPI спецификации.
        """
        endpoints = []
        paths = spec_dict.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                    endpoint_info = {
                        "method": method.upper(),
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": (details.get("description", "") or "")[:150],  # Limit description
                    }

                    # Добавляем информацию о параметрах если есть
                    if "parameters" in details:
                        params = [f"{p.get('name')} ({p.get('in')})" for p in details["parameters"][:5]]
                        if params:
                            endpoint_info["parameters"] = params

                    # Добавляем информацию о request body если есть
                    if "requestBody" in details:
                        endpoint_info["has_request_body"] = True

                    # Добавляем коды ответов
                    responses = list(details.get("responses", {}).keys())[:5]
                    if responses:
                        endpoint_info["response_codes"] = responses

                    endpoints.append(endpoint_info)

        return endpoints

    async def generate_from_ui_model(self, ui_model: UiModel) -> TestSuite:
        # Формируем текст требований из UI модели
        requirements_text = "Generate test cases for the following UI:\n\n"

        for page in ui_model.pages:
            requirements_text += f"Page: {page.name}\nURL: {page.url}\n\n"
            requirements_text += "Elements:\n"
            for element in page.elements:
                requirements_text += f"- {element.type} '{element.name}' (locator: {element.locator}, role: {element.role})\n"
            requirements_text += f"\nMain flows: {', '.join(page.main_flows)}\n\n"

        # Используем существующий метод генерации
        return await self.generate_from_requirements_text(requirements_text)
