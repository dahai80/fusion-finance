from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ...ai_client import MLXClient
from ...exceptions import DataError
from ...statements.analyzer import FinancialStatement, StatementAnalyzer
from ...statements.normalizer import StatementNormalizer
from ...statements.screener import FinancialScreener, ScreenFilter

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


class NormalizeRequest(BaseModel):
    data: dict[str, Any]
    standard: str = "A"
    company: str = ""
    period: str = ""


class TrendRequest(BaseModel):
    statements: list[MetricsRequest]


def _get_mlx() -> MLXClient:
    return MLXClient()


@router.post("/analyze", summary="AI财报分析")
async def analyze_statements(req: AnalyzeRequest):
    try:
        analyzer = StatementAnalyzer(_get_mlx())
        result = await analyzer.analyze_statements(req.company, req.data)
        return {"company": req.company, "analysis": result}
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="analyze_statements failed", detail=str(e), field="analyze_statements")


@router.post("/metrics", summary="纯财务指标计算(无AI)")
async def calculate_metrics(req: MetricsRequest):
    try:
        stmt = FinancialStatement(
            company=req.company,
            period=req.period,
            revenue=req.revenue,
            gross_profit=req.gross_profit,
            operating_income=req.operating_income,
            net_income=req.net_income,
            total_assets=req.total_assets,
            total_liabilities=req.total_liabilities,
            equity=req.equity,
            operating_cf=req.operating_cf,
            free_cf=req.free_cf,
        )
        analyzer = StatementAnalyzer()
        analysis = analyzer.calculate_metrics(stmt)
        return asdict(analysis)
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="calculate_metrics failed", detail=str(e), field="calculate_metrics")


@router.post("/validate", summary="资产负债表勾稽校验")
async def validate_balance_sheet(req: ValidateRequest):
    try:
        stmts = []
        for s in req.statements:
            stmts.append(
                FinancialStatement(
                    company=s.company,
                    period=s.period,
                    revenue=s.revenue,
                    gross_profit=s.gross_profit,
                    operating_income=s.operating_income,
                    net_income=s.net_income,
                    total_assets=s.total_assets,
                    total_liabilities=s.total_liabilities,
                    equity=s.equity,
                    operating_cf=s.operating_cf,
                    free_cf=s.free_cf,
                )
            )
        analyzer = StatementAnalyzer()
        issues = analyzer.validate_balance_sheet(stmts)
        return {"total_checked": len(stmts), "issues": issues, "valid": len(issues) == 0}
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="validate_balance_sheet failed", detail=str(e), field="validate_balance_sheet")


@router.post("/screener", summary="股票筛选器")
async def screener(req: ScreenerRequest):
    try:
        screener = FinancialScreener()
        screener.load_sample_data()
        preset = ""
        filters = None
        if req.filters:
            preset = req.filters.get("preset", "")
            if preset:
                filters = None
            else:
                raw = req.filters.get("filters", [])
                filters = [
                    ScreenFilter(metric=f.get("metric", ""), min_val=f.get("min"), max_val=f.get("max"))
                    for f in raw
                    if f.get("metric")
                ]
        result = screener.screen_and_rank(filters=filters, preset=preset, limit=req.limit)
        return result
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="screener failed", detail=str(e), field="screener")


@router.post("/normalize", summary="财报数据标准化")
async def normalize_statement(req: NormalizeRequest):
    try:
        normalizer = StatementNormalizer(standard=req.standard)
        stmt = normalizer.normalize(req.data, company=req.company, period=req.period)
        return asdict(stmt)
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="normalize_statement failed", detail=str(e), field="normalize_statement")


@router.post("/trend", summary="多期趋势分析")
async def trend_analysis(req: TrendRequest):
    try:
        stmts = []
        for s in req.statements:
            stmts.append(
                FinancialStatement(
                    company=s.company,
                    period=s.period,
                    revenue=s.revenue,
                    gross_profit=s.gross_profit,
                    operating_income=s.operating_income,
                    net_income=s.net_income,
                    total_assets=s.total_assets,
                    total_liabilities=s.total_liabilities,
                    equity=s.equity,
                    operating_cf=s.operating_cf,
                    free_cf=s.free_cf,
                )
            )
        return StatementNormalizer.trend_analysis(stmts)
    except DataError:
        raise
    except Exception as e:
        raise DataError(message="trend_analysis failed", detail=str(e), field="trend_analysis")


@router.get("/standards", summary="支持的会计准则列表")
async def list_standards():
    return {"standards": StatementNormalizer.list_standards()}


@router.get("/screener-presets", summary="筛选器预设列表")
async def screener_presets():
    s = FinancialScreener()
    return {"presets": s.list_presets()}
