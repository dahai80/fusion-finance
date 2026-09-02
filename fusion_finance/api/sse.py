from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from ..config import get_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[channel].append(q)
        logger.debug("SSE subscriber added to channel: %s", channel)
        return q

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        if channel in self._subscribers:
            with contextlib.suppress(ValueError):
                self._subscribers[channel].remove(queue)

    async def publish(self, channel: str, data: dict[str, Any]):
        event_str = json.dumps(data, ensure_ascii=False, default=str)
        for q in self._subscribers.get(channel, []):
            try:
                await q.put(event_str)
            except Exception as e:
                logger.warning("SSE publish failed: %s", e)


event_bus = EventBus()


async def _sse_stream(queue: asyncio.Queue, keepalive_interval: int = 15):
    last_keepalive = time.time()
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"data: {data}\n\n"
                last_keepalive = time.time()
            except TimeoutError:
                if time.time() - last_keepalive >= keepalive_interval:
                    yield ": keepalive\n\n"
                    last_keepalive = time.time()
    except asyncio.CancelledError:
        pass
    except GeneratorExit:
        pass


@router.get("/insights")
async def insights_stream(session_id: str = Query(default="default")):
    from starlette.responses import StreamingResponse

    channel = f"insights:{session_id}"
    queue = event_bus.subscribe(channel)

    async def generate():
        try:
            async for chunk in _sse_stream(queue):
                yield chunk
        finally:
            event_bus.unsubscribe(channel, queue)
            logger.debug("SSE unsubscribed from channel: %s", channel)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/alerts")
async def alerts_stream(session_id: str = Query(default="default")):
    from starlette.responses import StreamingResponse

    channel = f"alerts:{session_id}"
    queue = event_bus.subscribe(channel)

    async def generate():
        try:
            async for chunk in _sse_stream(queue):
                yield chunk
        finally:
            event_bus.unsubscribe(channel, queue)
            logger.debug("SSE unsubscribed from channel: %s", channel)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/publish")
async def publish_event(
    request: Request,
    channel: str,
    data: dict[str, Any],
    x_api_key: str = Header(default=""),
):
    configured_key = get_api_key()
    if not configured_key:
        logger.warning(
            "SSE /events/publish accepted without API key configured (channel=%s, client=%s) — local-dev mode",
            channel,
            request.client.host if request.client else "unknown",
        )
    else:
        if not hmac.compare_digest(x_api_key, configured_key):
            logger.warning(
                "SSE /events/publish rejected: invalid API key (channel=%s, client=%s)",
                channel,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )
    await event_bus.publish(channel, data)
    return {"status": "published", "channel": channel}
