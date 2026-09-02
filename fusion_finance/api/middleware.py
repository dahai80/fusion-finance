from __future__ import annotations

import hmac
import logging
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..utils.audit import get_audit_trail

logger = logging.getLogger(__name__)

_SENSITIVE_QUERY_KEYS = {"token", "key", "api_key", "password", "secret"}


def _redact_query(query_str: str) -> str:
    if not query_str:
        return ""
    parts = []
    for kv in query_str.lstrip("?").split("&"):
        if "=" in kv:
            k, _ = kv.split("=", 1)
            if k.lower() in _SENSITIVE_QUERY_KEYS:
                parts.append(f"{k}=***")
            else:
                parts.append(kv)
        else:
            parts.append(kv)
    return "&".join(parts)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        try:
            audit = get_audit_trail()
            user = request.headers.get("x-auth-user", "") or "anonymous"
            query_redacted = _redact_query(str(request.query_params))
            audit.record(
                user=user,
                action=f"{request.method} {request.url.path}",
                module="api",
                details={"query": query_redacted[:500], "status": response.status_code},
                status="success" if response.status_code < 400 else "error",
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            logger.error("Audit middleware failed (request still served): %s", e)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/api/v1/", "/api/v1/ready", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app: Any, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counts: dict[str, list[float]] = {}

    def _key(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def _check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        bucket = [t for t in self._counts.get(key, []) if t > cutoff]
        if len(bucket) >= self.max_requests:
            self._counts[key] = bucket
            return False
        bucket.append(now)
        self._counts[key] = bucket
        return True

    def _prune_keys(self) -> None:
        if len(self._counts) <= 10000:
            return
        cutoff = time.time() - self.window_seconds
        self._counts = {k: v for k, v in self._counts.items() if any(t > cutoff for t in v)}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        key = self._key(request)
        if not self._check(key):
            self._prune_keys()
            logger.warning("Rate limit exceeded for %s", key)
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        self._prune_keys()
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
        if not hmac.compare_digest(provided, self.api_key):
            logger.warning("Invalid API key from %s for %s", request.client, request.url.path)
            return Response(
                content='{"detail":"Invalid API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
