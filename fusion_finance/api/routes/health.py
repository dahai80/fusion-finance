from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from ... import __version__
from ..dependencies import get_mlx_client

logger = logging.getLogger(__name__)

router = APIRouter()

VERSION = __version__


@router.get("/", summary="健康检查")
async def health_check():
    return {"status": "ok", "version": VERSION, "service": "fusion-finance"}


@router.get("/ready", summary="就绪检查")
async def readiness_check(response: Response, client=Depends(get_mlx_client)):
    try:
        result = await client.health_check()
        if result.get("status") == "ok":
            return {"status": "ready", "mlx": "connected", "models": result.get("models", [])}
        logger.warning("MLX health check returned non-ok: %s", result)
        response.status_code = 503
        return {"status": "degraded", "mlx": "error", "detail": result.get("detail", "unknown")}
    except Exception as e:
        logger.error("Readiness check failed: %s", e)
        response.status_code = 503
        return {"status": "degraded", "mlx": "unreachable", "detail": "unreachable"}
