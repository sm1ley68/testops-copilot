from fastapi import FastAPI

from .config import settings

app = FastAPI(title="TestOps Copilot API", version="0.1.0")


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "env": settings.app_env,
        "cloudru_api_url": settings.cloudru_api_url,
    }
