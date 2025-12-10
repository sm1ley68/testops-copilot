from app.agents.html_agent import HtmlAnalysisAgent
from app.agents.requirements_agent import RequirementsAgent
from app.agents.automation_agent import AutomationAgent
from app.agents.coverage_agent import CoverageAgent
from app.models import CoverageReport, TestSuite


class CoordinatorAgent:
    def __init__(self) -> None:
        self.html_agent = HtmlAnalysisAgent()
        self.req_agent = RequirementsAgent()
        self.auto_agent = AutomationAgent()
        self.cov_agent = CoverageAgent()

    async def full_ui_flow(
        self,
        *,
        url: str | None,
        html: str | None,
        requirements_text: str | None,
    ) -> CoverageReport:
        # 1. Источник требований
        if requirements_text:
            suite: TestSuite = await self.req_agent.generate_from_requirements_text(
                requirements_text
            )
        else:
            ui_model = await self.html_agent.analyze(url=url, html=html)
            suite = await self.req_agent.generate_from_ui_model(ui_model)

        # 2. Генерация e2e
        auto_tests = await self.auto_agent.generate_e2e_tests(suite, url or "http://localhost")

        # 3. Покрытие
        report = await self.cov_agent.analyze(suite, auto_tests)
        return report
