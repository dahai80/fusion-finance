from __future__ import annotations

import logging

from fastapi import APIRouter

from ...ai_client import MLXClient

logger = logging.getLogger(__name__)

router = APIRouter()

VERSION = "0.2.0"


@router.get("/", summary="健康检查")
async def health_check():
    return {"status": "ok", "version": VERSION, "service": "fusion-finance"}


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    try:
        client = MLXClient()
        result = await client.health_check()
        if result.get("status") == "ok":
            return {"status": "ready", "mlx": "connected", "models": result.get("models", [])}
        logger.warning("MLX health check returned non-ok: %s", result)
        return {"status": "degraded", "mlx": "error", "detail": result.get("detail", "unknown")}
    except Exception as e:
        logger.error("Readiness check failed: %s", e)
        return {"status": "degraded", "mlx": "unreachable", "detail": str(e)}
