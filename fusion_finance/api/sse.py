from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query

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

    queue = event_bus.subscribe(f"insights:{session_id}")

    async def generate():
        async for chunk in _sse_stream(queue):
            yield chunk

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

    queue = event_bus.subscribe(f"alerts:{session_id}")

    async def generate():
        async for chunk in _sse_stream(queue):
            yield chunk

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
async def publish_event(channel: str, data: dict[str, Any]):
    await event_bus.publish(channel, data)
    return {"status": "published", "channel": channel}
