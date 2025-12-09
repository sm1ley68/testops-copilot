from app.models import TestSuite, AutomatedTest, CoverageReport


class CoverageAgent:
    """
    Агент анализа покрытия.
    """
    async def analyze(
        self,
        suite: TestSuite,
        auto_tests: list[AutomatedTest] | None = None,
    ) -> CoverageReport:
        titles = [c.title for c in suite.cases]
        summary = f"Сгенерировано {len(suite.cases)} тест-кейсов. " \
                  f"Автотестов: {len(auto_tests) if auto_tests else 0}."

        return CoverageReport(
            covered_features=titles,
            missing_features=[],
            duplicates=[],
            summary=summary,
            test_suite=suite,
            automated_tests=auto_tests or [],
        )
