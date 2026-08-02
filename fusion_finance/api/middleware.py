from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..utils.audit import AuditTrail

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        try:
            audit = AuditTrail()
            audit.record(
                user=request.headers.get("x-user", "anonymous"),
                action=f"{request.method} {request.url.path}",
                module="api",
                details={"query": str(request.query_params), "status": response.status_code},
                status="success" if response.status_code < 400 else "error",
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            logger.warning("Audit middleware failed: %s", e)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counts: dict[str, list[float]] = defaultdict(list)

    def _key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._counts[key] = [t for t in self._counts[key] if t > cutoff]
        if len(self._counts[key]) >= self.max_requests:
            return False
        self._counts[key].append(now)
        return True

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = self._key(request)
        if not self._check(key):
            logger.warning("Rate limit exceeded for %s", key)
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)


class APIKeyMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/api/v1/", "/api/v1/ready", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app: Any, api_key: str = ""):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.api_key:
            return await call_next(request)

        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        provided = request.headers.get("x-api-key", "")
        if provided != self.api_key:
            logger.warning("Invalid API key from %s for %s", request.client, request.url.path)
            return Response(
                content='{"detail":"Invalid API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
