from fastapi import APIRouter, HTTPException

from app.agents.validation_agent import ValidationAgent
from app.models import TestSuite, ValidationReport

router = APIRouter(prefix="/validation", tags=["validation"])

agent = ValidationAgent()


@router.post("/standards", response_model=ValidationReport)
async def validate_test_suite_standards(suite: TestSuite):
    try:
        report = await agent.validate_test_suite(suite)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return report
