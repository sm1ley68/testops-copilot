from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import TestSuite, CoverageReport
from app.agents.coverage_agent import CoverageAgent

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("/analyze", response_model=CoverageReport)
async def analyze_suite(test_suite: TestSuite):
    """
    Анализирует тест-сьют на:
    - Дубликаты тестов
    - Пробелы в покрытии
    - Предложения по улучшению

    Использует LLM для интеллектуального анализа.
    """
    try:
        agent = CoverageAgent()
        report = await agent.analyze(test_suite)
        return report

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze test suite: {str(e)}"
        )
