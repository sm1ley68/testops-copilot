from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/generation", tags=["generation"])


class UiRequirements(BaseModel):
    title: str
    description: str


@router.post("/manual/ui")
async def generate_manual_ui_test_cases(req: UiRequirements):
    # заглушка — потом здесь будет вызов Cloud.ru LLM
    return {
        "message": "UI manual test cases generated (stub)",
        "input": req.model_dump(),
    }
