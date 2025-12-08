from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/optimization", tags=["optimization"])


class TestSuite(BaseModel):
    cases: list[str]


@router.post("/analyze")
async def analyze_suite(payload: TestSuite):
    return {
        "duplicates": [],
        "gaps": [],
        "suggestions": [],
    }
