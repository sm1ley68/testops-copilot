# backend/app/routers/chat.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from app.llm_client import get_llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]  # Вся история чата
    stream: Optional[bool] = True  # По умолчанию streaming


class ChatResponse(BaseModel):
    message: str
    role: str = "assistant"


@router.post("/completions")
async def chat_completion(request: ChatRequest):
    try:
        print(f"[Chat] Received {len(request.messages)} messages (history included)")

        # Системный промпт для чат-бота
        system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant specialized in software testing, QA, and test automation.

You can help with:
- Explaining testing concepts (unit tests, integration tests, e2e, API testing)
- Advising on test automation strategies
- Answering questions about Allure, pytest, Playwright, Selenium
- Discussing CI/CD and DevOps practices
- General QA and testing best practices

Be concise, friendly, and technical when needed. If user asks about generating tests, 
suggest using the dedicated buttons for test generation (UI Tests, API Tests, etc.).

Remember the conversation history and maintain context across messages."""
        }

        # Формируем сообщения для LLM (вся история + новое сообщение)
        llm_messages = [system_message] + [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        print(f"[Chat] Sending {len(llm_messages)} messages to LLM (including system prompt)")

        # Если streaming запрошен
        if request.stream:
            async def generate():
                try:
                    with get_llm_client() as client:
                        resp = client.post(
                            "/chat/completions",
                            json={
                                "model": "openai/gpt-oss-120b",
                                "messages": llm_messages,
                                "temperature": 0.8,
                                "max_tokens": 1500,
                                "stream": True
                            },
                            stream=True,
                            timeout=300
                        )

                        for line in resp.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith('data: '):
                                    yield decoded_line + '\n\n'

                except Exception as e:
                    error_data = {
                        "error": str(e),
                        "type": "stream_error"
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )

        # Обычный режим (без стриминга)
        with get_llm_client() as client:
            resp = client.post(
                "/chat/completions",
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": llm_messages,
                    "temperature": 0.8,
                    "max_tokens": 1500,
                },
                timeout=300
            )

        if resp.status_code != 200:
            print(f"[Chat] LLM API error: {resp.status_code}")
            raise Exception(f"LLM API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        assistant_message = data["choices"][0]["message"]["content"]

        print(f"[Chat] Response length: {len(assistant_message)} characters")

        return ChatResponse(message=assistant_message, role="assistant")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )
