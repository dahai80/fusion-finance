from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...config import get_api_key
from ...utils.audit import get_audit_trail

logger = logging.getLogger(__name__)

router = APIRouter()
_audit = get_audit_trail()


def _server_user(request: Request) -> str:
    api_key = request.headers.get("x-api-key", "") or request.headers.get("authorization", "")
    return "api_client" if api_key else ""


class AuditRecordRequest(BaseModel):
    user: str = ""
    action: str
    module: str
    details: Any = ""
    status: str = "success"
    duration_ms: float = 0.0


class AuditQueryRequest(BaseModel):
    user: str = ""
    action: str = ""
    module: str = ""
    status: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


def _require_auth(request: Request) -> None:
    api_key = get_api_key()
    if not api_key:
        return
    provided = (
        request.headers.get("x-api-key", "") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    if not provided or not hmac.compare_digest(provided, api_key):
        logger.warning("audit route rejected unauthenticated request")
        raise HTTPException(status_code=401, detail="unauthorized")


@router.post("/record", summary="记录审计日志")
async def record_audit(req: AuditRecordRequest, request: Request):
    _require_auth(request)
    actor = _server_user(request)
    if actor:
        audit_user = actor
        details = req.details
        if req.user and req.user != actor:
            details = {"submitted_user": req.user, "payload": details}
    else:
        audit_user = req.user or "local"
        details = req.details
    try:
        entry = _audit.record(
            user=audit_user,
            action=req.action,
            module=req.module,
            details=details,
            status=req.status,
            duration_ms=req.duration_ms,
        )
        return {"timestamp": entry.timestamp, "status": "ok", "user": audit_user}
    except Exception as e:
        logger.error("record_audit failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error")


@router.post("/query", summary="查询审计日志")
async def query_audit(req: AuditQueryRequest, request: Request):
    _require_auth(request)
    try:
        entries = _audit.query(
            user=req.user,
            action=req.action,
            module=req.module,
            status=req.status,
            start_time=req.start_time,
            end_time=req.end_time,
            limit=req.limit,
            offset=req.offset,
        )
        return {
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "user": e.user,
                    "action": e.action,
                    "module": e.module,
                    "details": e.details,
                    "status": e.status,
                    "duration_ms": e.duration_ms,
                }
                for e in entries
            ],
            "count": len(entries),
        }
    except Exception as e:
        logger.error("query_audit failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/stats", summary="审计统计")
async def audit_stats(request: Request):
    _require_auth(request)
    try:
        return _audit.get_stats_from_file()
    except Exception as e:
        logger.error("audit_stats failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/file-stats", summary="审计文件统计(全量)", deprecated=True)
async def audit_file_stats(request: Request):
    _require_auth(request)
    return await audit_stats(request)


@router.get("/verify-chain", summary="校验审计哈希链完整性")
async def verify_chain(request: Request):
    _require_auth(request)
    try:
        return _audit.verify_chain()
    except Exception as e:
        logger.error("verify_chain failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error")
