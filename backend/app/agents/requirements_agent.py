from app.models import UiModel, TestCase, TestSuite


class RequirementsAgent:
    """
    Агент, который по UiModel или тексту требований генерирует TestSuite.
    Пока заглушка: делает один простой кейс.
    """

    async def generate_from_ui_model(self, ui: UiModel) -> TestSuite:
        cases: list[TestCase] = []

        for page in ui.pages:
            cases.append(
                TestCase(
                    title=f"Отображение страницы {page.name}",
                    description=f"Проверить, что страница {page.url} открывается без ошибок.",
                    steps=[
                        f"Открыть страницу {page.url}",
                        "Убедиться, что основной контент отображается.",
                    ],
                    expected_result="Страница отображается без ошибок, основные элементы видимы.",
                    priority="NORMAL",
                    tags=["ui", "smoke"],
                )
            )

        return TestSuite(name="UI suite (stub)", cases=cases)

    async def generate_from_requirements_text(self, text: str) -> TestSuite:
        # заглушка для случая, когда фронт присылает сразу текст требований
        case = TestCase(
            title="Сценарий из текстовых требований",
            description=text,
            steps=["Шаги определяются на основе описания."],
            expected_result="Ожидаемый результат определён в описании.",
            priority="NORMAL",
            tags=["ui"],
        )
        return TestSuite(name="Text-based suite (stub)", cases=[case])
