from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.requirements_agent import RequirementsAgent

router = APIRouter(prefix="/generation", tags=["generation"])

agent = RequirementsAgent()


class PromptPayload(BaseModel):
    prompt: str


@router.post("/manual/ui")
async def generate_manual_ui_test_cases(payload: PromptPayload):
    try:
        code = await agent.generate_from_prompt(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"generated_code": code}
