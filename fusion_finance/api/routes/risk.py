from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...exceptions import RiskError
from ...risk.advanced_risk import RiskModelingEngine, StressTestResult
from ...risk.engine import RiskComplianceEngine
from ...risk.entity_resolution import EntityResolver
from ...risk.sanctions import SanctionsEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class KYCRequest(BaseModel):
    entity: str
    jurisdiction: str = "CN"


class CreditRequest(BaseModel):
    entity: str
    financials: dict[str, float] = Field(default_factory=dict)


class ComplianceRequest(BaseModel):
    contract: str
    regulations: str = "中国公司法"


class VaRRequest(BaseModel):
    returns: list[float] = Field(default_factory=list)
    portfolio_value: float = 1_000_000
    confidence: float = 0.95


class MonteCarloVaRRequest(BaseModel):
    portfolio_value: float = 1_000_000
    mu: float = 0.08
    sigma: float = 0.20
    days: int = 252
    simulations: int = 10000


class StressTestRequest(BaseModel):
    scenario: str = ""
    impact: float = 0.0
    probability: str = "medium"
    affected_factors: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)


def _get_mlx() -> MLXClient:
    return MLXClient()


@router.post("/kyc", summary="AI KYC尽职调查")
async def kyc_screening(req: KYCRequest):
    try:
        engine = RiskComplianceEngine(_get_mlx())
        result = await engine.kyc_screening(req.entity, req.jurisdiction)
        return asdict(result)
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="kyc_screening failed", detail=str(e), risk_type="kyc_screening")


@router.post("/credit", summary="AI信用评估")
async def credit_assessment(req: CreditRequest):
    try:
        engine = RiskComplianceEngine(_get_mlx())
        result = await engine.credit_assessment(req.entity, req.financials)
        return asdict(result)
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="credit_assessment failed", detail=str(e), risk_type="credit_assessment")


@router.post("/compliance", summary="AI合规审查")
async def compliance_check(req: ComplianceRequest):
    try:
        engine = RiskComplianceEngine(_get_mlx())
        result = await engine.compliance_check(req.contract, req.regulations)
        return result
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="compliance_check failed", detail=str(e), risk_type="compliance_check")


@router.post("/var", summary="VaR风险价值计算(纯数学)")
async def calculate_var(req: VaRRequest):
    try:
        result = RiskModelingEngine.calculate_var(req.returns, req.portfolio_value, req.confidence)
        return asdict(result)
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="calculate_var failed", detail=str(e), risk_type="calculate_var")


@router.post("/var/monte-carlo", summary="蒙特卡洛VaR(纯数学)")
async def monte_carlo_var(req: MonteCarloVaRRequest):
    try:
        result = RiskModelingEngine.monte_carlo_var(
            req.portfolio_value,
            req.mu,
            req.sigma,
            req.days,
            req.simulations,
        )
        return asdict(result)
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="monte_carlo_var failed", detail=str(e), risk_type="monte_carlo_var")


@router.get("/stress-scenarios", summary="获取压力测试预设场景")
async def get_stress_scenarios():
    try:
        scenarios = RiskModelingEngine.stress_test_scenarios()
        return {"scenarios": [asdict(s) for s in scenarios]}
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="get_stress_scenarios failed", detail=str(e), risk_type="get_stress_scenarios")


@router.post("/stress-test", summary="自定义压力测试")
async def run_stress_test(req: StressTestRequest):
    try:
        result = StressTestResult(
            scenario=req.scenario,
            impact=req.impact,
            probability=req.probability,
            affected_factors=req.affected_factors,
            mitigations=req.mitigations,
        )
        logger.info("Stress test: scenario=%s, impact=%.2f", req.scenario, req.impact)
        return asdict(result)
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="run_stress_test failed", detail=str(e), risk_type="run_stress_test")


class SanctionsScreenRequest(BaseModel):
    entity: str
    threshold: float = 0.6


class SanctionsBatchRequest(BaseModel):
    entities: list[str] = Field(default_factory=list)
    threshold: float = 0.6


class EntityGraphRequest(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class UBORequest(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    target_entity_id: str = ""
    threshold: float = 0.25


_sanctions_engine = SanctionsEngine()
_entity_resolver = EntityResolver()


@router.post("/sanctions", summary="制裁名单筛查(纯逻辑)")
async def sanctions_screen(req: SanctionsScreenRequest):
    try:
        matches = _sanctions_engine.screen(req.entity, req.threshold)
        return {"entity": req.entity, "matches": [asdict(m) for m in matches], "hit_count": len(matches)}
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="sanctions_screen failed", detail=str(e), risk_type="sanctions_screen")


@router.post("/sanctions/batch", summary="批量制裁名单筛查(纯逻辑)")
async def sanctions_batch(req: SanctionsBatchRequest):
    try:
        results = _sanctions_engine.screen_batch(req.entities, req.threshold)
        return {
            "results": {k: [asdict(m) for m in v] for k, v in results.items()},
            "total_entities": len(req.entities),
        }
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="sanctions_batch failed", detail=str(e), risk_type="sanctions_batch")


@router.post("/entity-graph", summary="实体关系图谱(纯逻辑)")
async def entity_graph(req: EntityGraphRequest):
    try:
        graph = _entity_resolver.build_from_structure({"nodes": req.nodes, "edges": req.edges})
        return graph.to_dict()
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="entity_graph failed", detail=str(e), risk_type="entity_graph")


@router.post("/entity-graph/ubo", summary="UBO最终受益人解析(纯逻辑)")
async def resolve_ubo(req: UBORequest):
    try:
        graph = _entity_resolver.build_from_structure({"nodes": req.nodes, "edges": req.edges})
        ubos = _entity_resolver.resolve_ubo(graph, req.target_entity_id, req.threshold)
        pep_connections = _entity_resolver.find_pep_connections(graph)
        return {"target_entity_id": req.target_entity_id, "ubos": ubos, "pep_connections": pep_connections}
    except RiskError:
        raise
    except Exception as e:
        raise RiskError(message="resolve_ubo failed", detail=str(e), risk_type="resolve_ubo")
