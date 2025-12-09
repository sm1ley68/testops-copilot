from fastapi import FastAPI

from app.config import settings
from app.routers import generation, validation, optimization, requirements

app = FastAPI(title="TestOps Copilot API", version="0.1.0")

app.include_router(generation.router)
app.include_router(validation.router)
app.include_router(optimization.router)
app.include_router(requirements.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "env": settings.app_env,
        "cloudru_api_url": settings.cloudru_api_url,
    }
