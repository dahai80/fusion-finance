from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...ai_client import MLXClient
from ...config import get_api_key
from ...copilot import CopilotEngine

logger = logging.getLogger(__name__)

router = APIRouter()

_WS_MAX_CONNECTIONS = 50
_ws_connections: dict[str, int] = {}


def _check_auth(websocket: WebSocket) -> bool:
    api_key = get_api_key()
    if not api_key:
        return True
    provided = websocket.headers.get("x-api-key", "")
    if not provided:
        auth = websocket.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()
    return bool(provided) and provided == api_key


def _try_acquire(path: str) -> bool:
    count = _ws_connections.get(path, 0)
    if count >= _WS_MAX_CONNECTIONS:
        return False
    _ws_connections[path] = count + 1
    return True


def _release(path: str) -> None:
    count = _ws_connections.get(path, 0)
    if count <= 1:
        _ws_connections.pop(path, None)
    else:
        _ws_connections[path] = count - 1


@router.websocket("/copilot")
async def ws_copilot(websocket: WebSocket):
    if not _check_auth(websocket):
        logger.warning("WebSocket copilot rejected: unauthorized")
        await websocket.close(code=1011)
        return
    if not _try_acquire("copilot"):
        logger.warning("WebSocket copilot rejected: too many connections")
        await websocket.close(code=1013)
        return
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
                await websocket.send_json({"type": "error", "content": "internal error"})

    except WebSocketDisconnect:
        logger.info("WebSocket copilot session disconnected")
    except Exception as e:
        logger.error("WebSocket copilot error: %s", e)
    finally:
        _release("copilot")


@router.websocket("/modeling/progress")
async def ws_modeling_progress(websocket: WebSocket):
    if not _check_auth(websocket):
        logger.warning("WebSocket modeling rejected: unauthorized")
        await websocket.close(code=1011)
        return
    if not _try_acquire("modeling"):
        logger.warning("WebSocket modeling rejected: too many connections")
        await websocket.close(code=1013)
        return
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
                await websocket.send_json({"type": "error", "content": "unknown action"})

    except WebSocketDisconnect:
        logger.info("WebSocket modeling progress session disconnected")
    except Exception as e:
        logger.error("WebSocket modeling progress error: %s", e)
    finally:
        _release("modeling")
