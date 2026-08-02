from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...modeling.advanced import AdvancedModelingEngine, DDMModel, MergerModel
from ...modeling.engine import DCFModel, FinancialModelingEngine, InteractiveDCFSession
from ...modeling.portfolio import BlackLittermanOptimizer, PortfolioOptimizer, YieldCurve
from ...modeling.scenarios import ScenarioManager
from ...modeling.valuation import APVModel, EVAModel, RIModel

logger = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict[str, InteractiveDCFSession] = {}


class DCFBuildRequest(BaseModel):
    company: str
    revenue: list[float]
    assumptions: dict[str, Any] | None = None


class DCFCalculateRequest(BaseModel):
    company: str = ""
    forecast_years: int = 5
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0


class CompsBuildRequest(BaseModel):
    company: str
    industry: str
    peers: list[str] | None = None


class SensitivityRequest(BaseModel):
    company: str = ""
    forecast_years: int = 5
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    wacc_range: list[float] = Field(default_factory=lambda: [0.08, 0.09, 0.10, 0.11, 0.12])
    growth_range: list[float] = Field(default_factory=lambda: [0.01, 0.02, 0.03, 0.04, 0.05])


class MonteCarloRequest(BaseModel):
    company: str = ""
    forecast_years: int = 5
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    simulations: int = 1000


class LBOBuildRequest(BaseModel):
    company: str
    ebitda: list[float]
    assumptions: dict[str, Any] | None = None


class DDMRequest(BaseModel):
    company: str = ""
    current_dividend: float = 0.0
    growth_rate: float = 0.05
    required_return: float = 0.10


class MergerRequest(BaseModel):
    acquirer: str = ""
    target: str = ""
    acquirer_price: float = 0.0
    target_price: float = 0.0
    premium: float = 0.3


class APVRequest(BaseModel):
    company: str = ""
    unlevered_fcf: list[float] = Field(default_factory=list)
    unlevered_cost: float = 0.10
    debt: float = 0.0
    tax_rate: float = 0.25
    debt_cost: float = 0.05
    terminal_growth: float = 0.03


class EVARequest(BaseModel):
    company: str = ""
    nopat: list[float] = Field(default_factory=list)
    invested_capital: list[float] = Field(default_factory=list)
    wacc: float = 0.10


class RIRequest(BaseModel):
    company: str = ""
    book_value: float = 0.0
    net_income: list[float] = Field(default_factory=list)
    cost_of_equity: float = 0.12


class PortfolioOptimizeRequest(BaseModel):
    assets: list[str] = Field(default_factory=list)
    returns: list[float] = Field(default_factory=list)
    volatilities: list[float] = Field(default_factory=list)
    correlations: list[list[float]] = Field(default_factory=list)
    risk_free: float = 0.03
    num_simulations: int = 1000


class SessionCreateRequest(BaseModel):
    company: str
    assumptions: dict[str, Any] = Field(default_factory=dict)


class SessionUpdateRequest(BaseModel):
    key: str
    value: float


class ScenarioRequest(BaseModel):
    company: str = ""
    forecast_years: int = 5
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    custom_scenarios: dict[str, dict[str, float]] | None = None


def _get_mlx() -> MLXClient:
    return MLXClient()


@router.post("/dcf", summary="AI辅助构建DCF模型")
async def build_dcf(req: DCFBuildRequest):
    try:
        engine = FinancialModelingEngine(_get_mlx())
        model = await engine.build_dcf(req.company, req.revenue, req.assumptions)
        return asdict(model)
    except Exception as e:
        logger.error("build_dcf failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dcf/calculate", summary="纯DCF计算(无AI)")
async def calculate_dcf(req: DCFCalculateRequest):
    try:
        model = DCFModel(
            company=req.company,
            forecast_years=req.forecast_years,
            revenue=req.revenue,
            ebit_margin=req.ebit_margin,
            tax_rate=req.tax_rate,
            wacc=req.wacc,
            terminal_growth=req.terminal_growth,
            net_debt=req.net_debt,
            shares_outstanding=req.shares_outstanding,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_dcf failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comps", summary="AI辅助可比公司分析")
async def build_comps(req: CompsBuildRequest):
    try:
        engine = FinancialModelingEngine(_get_mlx())
        comps = await engine.build_comps(req.company, req.industry, req.peers)
        return asdict(comps)
    except Exception as e:
        logger.error("build_comps failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensitivity", summary="敏感性分析")
async def sensitivity_analysis(req: SensitivityRequest):
    try:
        model = DCFModel(
            company=req.company,
            forecast_years=req.forecast_years,
            revenue=req.revenue,
            ebit_margin=req.ebit_margin,
            tax_rate=req.tax_rate,
            wacc=req.wacc,
            terminal_growth=req.terminal_growth,
            net_debt=req.net_debt,
            shares_outstanding=req.shares_outstanding,
        )
        model.calculate()
        engine = FinancialModelingEngine()
        result = await engine.sensitivity_analysis(model, req.wacc_range, req.growth_range)
        return result
    except Exception as e:
        logger.error("sensitivity_analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monte-carlo", summary="蒙特卡洛模拟")
async def monte_carlo(req: MonteCarloRequest):
    try:
        model = DCFModel(
            company=req.company,
            forecast_years=req.forecast_years,
            revenue=req.revenue,
            ebit_margin=req.ebit_margin,
            tax_rate=req.tax_rate,
            wacc=req.wacc,
            terminal_growth=req.terminal_growth,
            net_debt=req.net_debt,
            shares_outstanding=req.shares_outstanding,
        )
        model.calculate()
        engine = FinancialModelingEngine()
        result = await engine.monte_carlo(model, req.simulations)
        return result
    except Exception as e:
        logger.error("monte_carlo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lbo", summary="AI辅助LBO模型")
async def build_lbo(req: LBOBuildRequest):
    try:
        engine = AdvancedModelingEngine(_get_mlx())
        model = await engine.build_lbo(req.company, req.ebitda, req.assumptions)
        return asdict(model)
    except Exception as e:
        logger.error("build_lbo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ddm", summary="DDM股利贴现计算")
async def calculate_ddm(req: DDMRequest):
    try:
        model = DDMModel(
            company=req.company,
            current_dividend=req.current_dividend,
            growth_rate=req.growth_rate,
            required_return=req.required_return,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_ddm failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merger", summary="并购模型计算")
async def calculate_merger(req: MergerRequest):
    try:
        model = MergerModel(
            acquirer=req.acquirer,
            target=req.target,
            acquirer_price=req.acquirer_price,
            target_price=req.target_price,
            premium=req.premium,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_merger failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apv", summary="APV调整现值计算")
async def calculate_apv(req: APVRequest):
    try:
        model = APVModel(
            company=req.company,
            unlevered_fcf=req.unlevered_fcf,
            unlevered_cost=req.unlevered_cost,
            debt=req.debt,
            tax_rate=req.tax_rate,
            debt_cost=req.debt_cost,
            terminal_growth=req.terminal_growth,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_apv failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/eva", summary="EVA经济增加值计算")
async def calculate_eva(req: EVARequest):
    try:
        model = EVAModel(
            company=req.company,
            nopat=req.nopat,
            invested_capital=req.invested_capital,
            wacc=req.wacc,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_eva failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ri", summary="RI剩余收益计算")
async def calculate_ri(req: RIRequest):
    try:
        model = RIModel(
            company=req.company,
            book_value=req.book_value,
            net_income=req.net_income,
            cost_of_equity=req.cost_of_equity,
        )
        result = model.calculate()
        return {"result": result, "model": asdict(model)}
    except Exception as e:
        logger.error("calculate_ri failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/optimize", summary="投资组合优化")
async def optimize_portfolio(req: PortfolioOptimizeRequest):
    try:
        portfolios = PortfolioOptimizer.efficient_frontier(
            req.returns,
            req.volatilities,
            req.correlations,
            req.risk_free,
            req.num_simulations,
        )
        max_sharpe = PortfolioOptimizer.max_sharpe(portfolios)
        min_vol = PortfolioOptimizer.min_volatility(portfolios)
        return {
            "assets": req.assets,
            "portfolios": portfolios[:50],
            "max_sharpe": max_sharpe,
            "min_volatility": min_vol,
            "total_simulated": len(portfolios),
        }
    except Exception as e:
        logger.error("optimize_portfolio failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/frontier", summary="有效前沿示例数据")
async def efficient_frontier_sample():
    try:
        returns = [0.12, 0.10, 0.15, 0.08]
        vols = [0.20, 0.15, 0.25, 0.12]
        n = len(returns)
        corr = [[1.0 if i == j else 0.3 for j in range(n)] for i in range(n)]
        portfolios = PortfolioOptimizer.efficient_frontier(returns, vols, corr)
        max_sharpe = PortfolioOptimizer.max_sharpe(portfolios)
        min_vol = PortfolioOptimizer.min_volatility(portfolios)
        return {
            "assets": ["Stock A", "Stock B", "Stock C", "Bond"],
            "frontier": portfolios[:50],
            "max_sharpe": max_sharpe,
            "min_volatility": min_vol,
        }
    except Exception as e:
        logger.error("efficient_frontier_sample failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session", summary="创建交互式DCF会话")
async def create_session(req: SessionCreateRequest):
    try:
        session = InteractiveDCFSession(req.company, req.assumptions)
        session_id = f"dcf_{req.company}_{id(session)}"
        _sessions[session_id] = session
        logger.info("Created session: %s", session_id)
        return {"session_id": session_id, "state": session.get_state()}
    except Exception as e:
        logger.error("create_session failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/{session_id}", summary="更新会话假设")
async def update_session(session_id: str, req: SessionUpdateRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    try:
        session = _sessions[session_id]
        result = session.update_assumption(req.key, req.value)
        return {"session_id": session_id, **result}
    except Exception as e:
        logger.error("update_session failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenarios", summary="情景分析对比")
async def scenario_compare(req: ScenarioRequest):
    try:
        model = DCFModel(
            company=req.company,
            forecast_years=req.forecast_years,
            revenue=req.revenue,
            ebit_margin=req.ebit_margin,
            tax_rate=req.tax_rate,
            wacc=req.wacc,
            terminal_growth=req.terminal_growth,
            net_debt=req.net_debt,
            shares_outstanding=req.shares_outstanding,
        )
        model.calculate()
        manager = ScenarioManager(model)
        if req.custom_scenarios:
            for name, adj in req.custom_scenarios.items():
                manager.add_scenario(name, adj)
        return {
            "base_result": model.calculate(),
            "comparison": manager.compare(),
            "summary": manager.get_summary(),
        }
    except Exception as e:
        logger.error("scenario_compare failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class BatchDCFRequest(BaseModel):
    models: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/batch-dcf", summary="批量DCF计算(纯数学)")
async def batch_dcf(req: BatchDCFRequest):
    try:
        results = FinancialModelingEngine.batch_dcf(req.models)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error("batch_dcf failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class BLRequest(BaseModel):
    market_weights: list[float] = Field(default_factory=list)
    cov_matrix: list[list[float]] = Field(default_factory=list)
    risk_aversion: float = 2.5
    views: list[list[float]] | None = None
    view_returns: list[float] | None = None
    tau: float = 0.05
    risk_free: float = 0.03


class YieldCurveRequest(BaseModel):
    maturities: list[float] = Field(default_factory=list)
    beta0: float = 0.04
    beta1: float = -0.02
    beta2: float = -0.01
    beta3: float = 0.0


class YieldCurveCalibrateRequest(BaseModel):
    observed_maturities: list[float] = Field(default_factory=list)
    observed_rates: list[float] = Field(default_factory=list)


@router.post("/portfolio/black-litterman", summary="Black-Litterman组合优化(纯数学)")
async def black_litterman(req: BLRequest):
    try:
        posterior = BlackLittermanOptimizer.posterior_returns(
            req.market_weights,
            req.cov_matrix,
            req.risk_aversion,
            req.views,
            req.view_returns,
            req.tau,
        )
        if not posterior:
            raise HTTPException(status_code=400, detail="参数不足或矩阵不可逆")
        result = BlackLittermanOptimizer.optimize(
            posterior,
            req.cov_matrix,
            req.risk_aversion,
            req.risk_free,
        )
        return {"posterior_returns": posterior, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("black_litterman failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yield-curve", summary="Nelson-Siegel收益率曲线(纯数学)")
async def yield_curve(req: YieldCurveRequest):
    try:
        yc = YieldCurve(beta0=req.beta0, beta1=req.beta1, beta2=req.beta2, beta3=req.beta3)
        rates = yc.nelson_siegel(req.maturities)
        return {"maturities": req.maturities, "rates": rates}
    except Exception as e:
        logger.error("yield_curve failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yield-curve/calibrate", summary="Nelson-Siegel参数校准(纯数学)")
async def yield_curve_calibrate(req: YieldCurveCalibrateRequest):
    try:
        yc = YieldCurve()
        params = yc.calibrate(req.observed_maturities, req.observed_rates)
        return params
    except Exception as e:
        logger.error("yield_curve_calibrate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
