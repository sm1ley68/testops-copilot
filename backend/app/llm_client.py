import httpx

from app.config import settings


def get_llm_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.cloudru_api_url,
        headers={
            "Authorization": f"Api-Key {settings.cloudru_api_token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
