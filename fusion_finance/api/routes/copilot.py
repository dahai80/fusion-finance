from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...copilot import CopilotEngine
from ...exceptions import AIClientError
from ..dependencies import get_copilot_engine, get_mlx_client

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


def _engine(
    mlx: MLXClient = Depends(get_mlx_client), shared: CopilotEngine = Depends(get_copilot_engine)
) -> CopilotEngine:
    if mlx is shared.mlx:
        return shared
    logger.debug("Building per-request CopilotEngine with injected MLXClient")
    return CopilotEngine(mlx)


@router.post("/chat", summary="AI Copilot对话")
async def chat(req: ChatRequest, engine: CopilotEngine = Depends(_engine)):
    try:
        result = await engine.chat(req.message, session_id=req.session_id)
        return ChatResponse(
            reply=result["reply"],
            tool_calls=result.get("tool_calls", []),
            rounds=result.get("rounds", 0),
            session_id=result.get("session_id", ""),
        )
    except AIClientError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copilot chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/history/{session_id}", summary="对话历史")
async def get_history(session_id: str, engine: CopilotEngine = Depends(_engine)):
    try:
        messages = engine.get_history(session_id)
        return {"session_id": session_id, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copilot history failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/sessions", summary="列出所有会话")
async def list_sessions(engine: CopilotEngine = Depends(_engine)):
    try:
        sessions = engine.memory.list_sessions()
        return {"sessions": sessions, "total": len(sessions)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copilot list_sessions failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="internal error")
