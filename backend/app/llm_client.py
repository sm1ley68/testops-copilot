from openai import OpenAI

from app.config import settings


def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=settings.cloudru_api_token,
        base_url=settings.cloudru_api_url,
    )
