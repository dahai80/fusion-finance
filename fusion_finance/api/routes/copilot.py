from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...copilot import CopilotEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    rounds: int = 0
    session_id: str = ""


@router.post("/chat", summary="AI Copilot对话")
async def chat(req: ChatRequest):
    try:
        mlx = MLXClient()
        engine = CopilotEngine(mlx)
        result = await engine.chat(req.message, session_id=req.session_id)
        return ChatResponse(
            reply=result["reply"],
            tool_calls=result.get("tool_calls", []),
            rounds=result.get("rounds", 0),
            session_id=result.get("session_id", ""),
        )
    except Exception as e:
        logger.error("copilot chat failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", summary="对话历史")
async def get_history(session_id: str):
    try:
        mlx = MLXClient()
        engine = CopilotEngine(mlx)
        messages = engine.get_history(session_id)
        return {"session_id": session_id, "messages": messages}
    except Exception as e:
        logger.error("copilot history failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", summary="列出所有会话")
async def list_sessions():
    try:
        mlx = MLXClient()
        engine = CopilotEngine(mlx)
        sessions = engine.memory.list_sessions()
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        logger.error("copilot list_sessions failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
