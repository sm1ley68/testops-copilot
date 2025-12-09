from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.requirements_agent import RequirementsAgent
from app.models import TestSuite

router = APIRouter(prefix="/requirements", tags=["Requirements"])


class RequirementsRequest(BaseModel):
    requirements_text: str


@router.post("/ui", response_model=TestSuite)
async def generate_ui_test_cases(req: RequirementsRequest):
    """
    Генерирует минимум 15 UI тест-кейсов напрямую через RequirementsAgent.
    Возвращает полный TestSuite с массивом cases.
    """
    agent = RequirementsAgent()
    suite = await agent.generate_from_requirements_text(req.requirements_text)
    return suite
