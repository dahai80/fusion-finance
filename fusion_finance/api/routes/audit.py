from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...utils.audit import AuditTrail

logger = logging.getLogger(__name__)

router = APIRouter()
_audit = AuditTrail()


class AuditRecordRequest(BaseModel):
    user: str
    action: str
    module: str
    details: str = ""
    status: str = "success"
    duration_ms: float = 0.0


class AuditQueryRequest(BaseModel):
    user: str = ""
    action: str = ""
    module: str = ""
    status: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    limit: int = 100
    offset: int = 0


@router.post("/record", summary="记录审计日志")
async def record_audit(req: AuditRecordRequest):
    try:
        entry = _audit.record(
            user=req.user, action=req.action, module=req.module,
            details=req.details, status=req.status, duration_ms=req.duration_ms,
        )
        return {"timestamp": entry.timestamp, "status": "ok"}
    except Exception as e:
        logger.error("record_audit failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", summary="查询审计日志")
async def query_audit(req: AuditQueryRequest):
    try:
        entries = _audit.query(
            user=req.user, action=req.action, module=req.module,
            status=req.status, start_time=req.start_time, end_time=req.end_time,
            limit=req.limit, offset=req.offset,
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="审计统计")
async def audit_stats():
    try:
        return _audit.get_stats()
    except Exception as e:
        logger.error("audit_stats failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-stats", summary="审计文件统计(全量)")
async def audit_file_stats():
    try:
        return _audit.get_stats_from_file()
    except Exception as e:
        logger.error("audit_file_stats failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
