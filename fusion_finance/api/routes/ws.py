from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...ai_client import MLXClient
from ...copilot import CopilotEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/copilot")
async def ws_copilot(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    try:
        mlx = MLXClient()
        engine = CopilotEngine(mlx)
        logger.info("WebSocket copilot session started")

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            user_message = msg.get("message", "")
            if not user_message:
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            await websocket.send_json({"type": "thinking", "content": "Processing..."})

            try:
                async for chunk in engine.chat_stream(user_message, session_id=session_id):
                    if session_id is None:
                        session_id = chunk.get("session_id")
                    await websocket.send_json(chunk)
                await websocket.send_json({"type": "done"})
            except Exception as e:
                logger.error("copilot stream error: %s", e)
                await websocket.send_json({"type": "error", "content": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket copilot session disconnected")
    except Exception as e:
        logger.error("WebSocket copilot error: %s", e)


@router.websocket("/modeling/progress")
async def ws_modeling_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        logger.info("WebSocket modeling progress session started")

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            action = msg.get("action", "")
            if action == "subscribe":
                await websocket.send_json({"type": "subscribed", "channel": msg.get("channel", "modeling")})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "error", "content": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("WebSocket modeling progress session disconnected")
    except Exception as e:
        logger.error("WebSocket modeling progress error: %s", e)
