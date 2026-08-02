from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...ai_client import MLXClient
from ...statements.analyzer import FinancialStatement, StatementAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    company: str
    data: dict[str, Any]


class MetricsRequest(BaseModel):
    company: str = ""
    period: str = ""
    revenue: float = 0.0
    gross_profit: float = 0.0
    operating_income: float = 0.0
    net_income: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    equity: float = 0.0
    operating_cf: float = 0.0
    free_cf: float = 0.0


class ValidateRequest(BaseModel):
    statements: list[MetricsRequest]


class ScreenerRequest(BaseModel):
    filters: dict[str, Any] | None = None
    limit: int = 20


def _get_mlx() -> MLXClient:
    return MLXClient()


@router.post("/analyze", summary="AI财报分析")
async def analyze_statements(req: AnalyzeRequest):
    try:
        analyzer = StatementAnalyzer(_get_mlx())
        result = await analyzer.analyze_statements(req.company, req.data)
        return {"company": req.company, "analysis": result}
    except Exception as e:
        logger.error("analyze_statements failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics", summary="纯财务指标计算(无AI)")
async def calculate_metrics(req: MetricsRequest):
    try:
        stmt = FinancialStatement(
            company=req.company, period=req.period,
            revenue=req.revenue, gross_profit=req.gross_profit,
            operating_income=req.operating_income, net_income=req.net_income,
            total_assets=req.total_assets, total_liabilities=req.total_liabilities,
            equity=req.equity, operating_cf=req.operating_cf, free_cf=req.free_cf,
        )
        analyzer = StatementAnalyzer()
        analysis = analyzer.calculate_metrics(stmt)
        return asdict(analysis)
    except Exception as e:
        logger.error("calculate_metrics failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", summary="资产负债表勾稽校验")
async def validate_balance_sheet(req: ValidateRequest):
    try:
        stmts = []
        for s in req.statements:
            stmts.append(FinancialStatement(
                company=s.company, period=s.period,
                revenue=s.revenue, gross_profit=s.gross_profit,
                operating_income=s.operating_income, net_income=s.net_income,
                total_assets=s.total_assets, total_liabilities=s.total_liabilities,
                equity=s.equity, operating_cf=s.operating_cf, free_cf=s.free_cf,
            ))
        analyzer = StatementAnalyzer()
        issues = analyzer.validate_balance_sheet(stmts)
        return {"total_checked": len(stmts), "issues": issues, "valid": len(issues) == 0}
    except Exception as e:
        logger.error("validate_balance_sheet failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screener", summary="股票筛选器(预留)")
async def screener(req: ScreenerRequest):
    return {
        "status": "placeholder",
        "message": "股票筛选器功能开发中",
        "filters": req.filters,
        "limit": req.limit,
    }
