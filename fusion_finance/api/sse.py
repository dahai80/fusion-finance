from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from ..config import get_api_key, verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


class EventBus:
    MAX_SUBSCRIBERS_PER_CHANNEL = 50
    MAX_QUEUE_SIZE = 256

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, channel: str) -> asyncio.Queue | None:
        subs = self._subscribers[channel]
        if len(subs) >= self.MAX_SUBSCRIBERS_PER_CHANNEL:
            logger.warning("SSE channel %s at subscriber cap %d, rejecting", channel, self.MAX_SUBSCRIBERS_PER_CHANNEL)
            return None
        q: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        subs.append(q)
        logger.debug("SSE subscriber added to channel: %s (total=%d)", channel, len(subs))
        return q

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        if channel in self._subscribers:
            with contextlib.suppress(ValueError):
                self._subscribers[channel].remove(queue)

    async def publish(self, channel: str, data: dict[str, Any]):
        event_str = json.dumps(data, ensure_ascii=False, default=str)
        for q in list(self._subscribers.get(channel, [])):
            try:
                q.put_nowait(event_str)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for channel %s, dropping event", channel)
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
    if queue is None:
        return JSONResponse(status_code=429, content={"detail": "subscriber cap reached"})

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
    if queue is None:
        return JSONResponse(status_code=429, content={"detail": "subscriber cap reached"})

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
    elif not verify_api_key(x_api_key):
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
