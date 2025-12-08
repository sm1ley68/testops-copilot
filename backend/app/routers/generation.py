from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from app.agents.coordinator import CoordinatorAgent
from app.models import CoverageReport

router = APIRouter(prefix="/generation", tags=["generation"])

coordinator = CoordinatorAgent()


class UiSourcePayload(BaseModel):
    url: Optional[HttpUrl] = None
    html: Optional[str] = None
    requirements_text: Optional[str] = None


@router.post("/ui/full", response_model=CoverageReport)
async def generate_full_ui_flow(payload: UiSourcePayload):
    try:
        report = await coordinator.full_ui_flow(
            url=str(payload.url) if payload.url else None,
            html=payload.html,
            requirements_text=payload.requirements_text,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return report
