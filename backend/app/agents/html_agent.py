from app.models import UiModel, UiPage, UiElement


class HtmlAnalysisAgent:
    async def analyze(self, *, url: str | None, html: str | None) -> UiModel:
        page = UiPage(
            url=url or "about:blank",
            name="Main page",
            elements=[
                UiElement(
                    type="button",
                    name="Добавить сервис",
                    locator="//button[contains(., 'Добавить сервис')]",
                    role="primary_action",
                )
            ],
            main_flows=["Основной пользовательский сценарий калькулятора цен"],
        )
        return UiModel(pages=[page])
