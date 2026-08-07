from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...exceptions import FinanceError
from ...modeling.engine import DCFModel
from ...modeling.scenarios import ScenarioManager
from ...risk.engine import RiskComplianceEngine
from ...statements.analyzer import StatementAnalyzer
from ...statements.screener import FinancialScreener

logger = logging.getLogger(__name__)

router = APIRouter()


class CompanyDashboardRequest(BaseModel):
    company: str
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    tax_rate: float = 0.25


class MarketDashboardRequest(BaseModel):
    preset: str = "quality"
    limit: int = 5


@router.post("/company", summary="公司全景仪表盘")
async def company_dashboard(req: CompanyDashboardRequest):
    result: dict[str, Any] = {"company": req.company}
    try:
        if req.revenue:
            model = DCFModel(
                company=req.company,
                revenue=req.revenue,
                ebit_margin=req.ebit_margin,
                wacc=req.wacc,
                terminal_growth=req.terminal_growth,
                net_debt=req.net_debt,
                shares_outstanding=req.shares_outstanding,
                tax_rate=req.tax_rate,
            )
            dcf_result = model.calculate()
            result["dcf"] = dcf_result
            manager = ScenarioManager(model)
            result["scenarios"] = manager.compare()
        else:
            result["dcf"] = None
            result["scenarios"] = None
    except Exception as e:
        logger.warning("company_dashboard dcf failed: %s", e)
        result["dcf"] = None
        result["scenarios"] = None

    try:
        StatementAnalyzer()
        metrics = {
            "gross_margin": round(req.ebit_margin[0] * 0.7, 2) if req.ebit_margin else None,
            "ebit_margin": req.ebit_margin[0] if req.ebit_margin else None,
        }
        result["key_metrics"] = metrics
    except Exception as e:
        logger.warning("company_dashboard metrics failed: %s", e)
        result["key_metrics"] = None

    try:
        RiskComplianceEngine()
        result["risk_summary"] = {"status": "available", "note": "Use /api/v1/risk/kyc for detailed screening"}
    except Exception as e:
        logger.warning("company_dashboard risk failed: %s", e)
        result["risk_summary"] = None

    logger.info("company_dashboard: %s", req.company)
    return result


@router.get("/market", summary="市场概览仪表盘")
async def market_dashboard(preset: str = "quality", limit: int = 5):
    try:
        screener = FinancialScreener()
        screener.load_sample_data()
        screened = screener.screen_and_rank(preset=preset, limit=limit)
        result: dict[str, Any] = {
            "screener": screened,
            "market_status": "simulated",
        }
        logger.info("market_dashboard: preset=%s, found=%d", preset, screened.get("passed_filter", 0))
        return result
    except Exception as e:
        logger.error("market_dashboard failed: %s", e)
        raise FinanceError(message="market_dashboard failed", detail=str(e))


@router.get("/status", summary="服务状态概览")
async def service_status():
    try:
        client = MLXClient()
        health = await client.health_check()
        mlx_status = "connected" if health.get("status") == "ok" else "error"
        models = health.get("models", [])
        if isinstance(models, list) and models and isinstance(models[0], dict):
            model_names = [m.get("id", m.get("model", "")) for m in models]
        elif isinstance(models, list):
            model_names = models
        else:
            model_names = []
    except Exception as e:
        logger.warning("service_status mlx check failed: %s", e)
        mlx_status = "unreachable"
        model_names = []

    return {
        "service": "fusion-finance",
        "version": "0.5.2",
        "mlx": {"status": mlx_status, "models": model_names},
        "modules": [
            "modeling",
            "statements",
            "risk",
            "report",
            "copilot",
            "chart",
            "project",
            "data",
            "audit",
        ],
    }
