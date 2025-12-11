from app.models import TestSuite, AutomatedTest, CoverageReport
from app.llm_client import get_llm_client
import json


class CoverageAgent:
    """
    Агент анализа покрытия с использованием LLM.
    """

    async def analyze(
            self,
            suite: TestSuite,
            auto_tests: list[AutomatedTest] | None = None,
    ) -> CoverageReport:
        """
        Анализирует тест-кейсы на дубликаты, пробелы и предлагает улучшения.
        """

        # Формируем описание тест-кейсов для LLM
        test_descriptions = []
        for case in suite.cases:
            test_descriptions.append({
                "title": case.title,
                "description": case.description,
                "tags": case.tags,
                "priority": case.priority
            })

        prompt = f"""Analyze the following test suite and provide:

1. **Duplicates**: Test cases that test the same functionality (similar titles/descriptions)
2. **Missing Coverage**: Important scenarios that are NOT covered by existing tests
3. **Suggestions**: Recommendations to improve the test suite

Test Suite: {suite.name}
Total Tests: {len(suite.cases)}

Test Cases:
{json.dumps(test_descriptions, indent=2, ensure_ascii=False)}

Return your analysis in this JSON format:
{{
  "duplicates": [
    {{"test1": "title1", "test2": "title2", "reason": "why they are duplicates"}}
  ],
  "missing_features": [
    {{"feature": "feature name", "reason": "why it should be tested"}}
  ],
  "suggestions": [
    {{"title": "suggestion", "description": "detailed recommendation"}}
  ]
}}
"""

        try:
            # Вызов LLM
            with get_llm_client() as client:
                resp = client.post(
                    "/chat/completions",
                    json={
                        "model": "openai/gpt-oss-120b",
                        "messages": [
                            {"role": "system", "content": "You are a QA expert analyzing test coverage."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    }
                )

            if resp.status_code != 200:
                raise Exception(f"LLM API error: {resp.status_code}")

            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # Парсим JSON из ответа
            # Убираем markdown блоки если есть
            if "```":
                content = content.split("```json").split("```")
            elif "```" in content:
                content = content.split("``````")[0]

            analysis = json.loads(content.strip())

            covered_features = [c.title for c in suite.cases]
            missing_features = [f"{item['feature']}: {item['reason']}"
                                for item in analysis.get("missing_features", [])]
            duplicates = [f"{item['test1']} ↔ {item['test2']}: {item['reason']}"
                            for item in analysis.get("duplicates", [])]
            suggestions = analysis.get("suggestions", [])

            summary = f"""Test Suite Analysis for '{suite.name}':
- Total Tests: {len(suite.cases)}
- Automated Tests: {len(auto_tests) if auto_tests else 0}
- Duplicates Found: {len(duplicates)}
- Missing Coverage: {len(missing_features)}
- Suggestions: {len(suggestions)}
"""

            return CoverageReport(
                covered_features=covered_features,
                missing_features=missing_features,
                duplicates=duplicates,
                summary=summary,
                test_suite=suite,
                automated_tests=auto_tests or [],
            )

        except Exception as e:
            print(f"[CoverageAgent] Error during analysis: {e}")
            # Fallback - возвращаем базовый отчет
            return CoverageReport(
                covered_features=[c.title for c in suite.cases],
                missing_features=["Unable to analyze missing features due to error"],
                duplicates=[],
                summary=f"Generated {len(suite.cases)} test cases. Analysis failed: {str(e)}",
                test_suite=suite,
                automated_tests=auto_tests or [],
            )
