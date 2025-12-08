from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/validation", tags=["validation"])


class TestCaseCode(BaseModel):
    code: str


@router.post("/check")
async def validate_test_case(payload: TestCaseCode):
    return {
        "is_valid": True,
        "issues": [],
    }
