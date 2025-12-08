from app.llm_client import get_llm_client


class RequirementsAgent:

    def __init__(self, model_name: str = "zai-org/GLM-4.6"):
        self._client = get_llm_client()
        self._model_name = model_name

    async def generate_from_prompt(self, user_prompt: str) -> str:
        # system-prompt: то, что задаёт роль и формат, он у нас «зашит» на бэке
        system_prompt = (
            "Ты опытный QA-инженер. Твоя задача — по входному описанию "
            "генерировать ручные UI тест-кейсы в формате Allure TestOps as Code (Python).\n"
            "Требования:\n"
            "- использовать паттерн AAA (Arrange-Act-Assert);\n"
            "- в каждом тесте использовать декораторы Allure "
            "(@allure.manual, @allure.feature, @allure.story, @allure.suite, "
            "@allure.title, @allure.tag, @allure.label(\"priority\", ...));\n"
            "- выводить ТОЛЬКО валидный Python-код без лишнего текста.\n"
        )

        # JSON-запрос к Cloud.ru Foundation Models (OpenAI-compatible)
        response = self._client.chat.completions.create(
            model=self._model_name,
            max_tokens=2000,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content or ""
