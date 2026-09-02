"""高级风控模型 — VaR、压力测试、情景分析。"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 30
_MAX_DEPTH = 20


@dataclass
class VaRResult:
    """VaR 计算结果。"""

    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    expected_shortfall: float = 0.0
    simulations: int = 0
    portfolio_value: float = 0.0
    confidence: float = 0.95


@dataclass
class StressTestResult:
    """压力测试结果。"""

    scenario: str = ""
    impact: float = 0.0
    probability: str = "low"
    affected_factors: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)


class RiskModelingEngine:
    """高级风控引擎 — VaR、压力测试、情景分析。"""

    @staticmethod
    def calculate_var(returns: list[float], portfolio_value: float = 1_000_000, confidence: float = 0.95) -> VaRResult:
        if not returns:
            logger.warning("calculate_var called with empty returns list")
            return VaRResult(confidence=confidence)
        n = len(returns)
        if n < _MIN_SAMPLES:
            logger.warning(
                "calculate_var sample size %d below floor %d; results are statistically unreliable",
                n,
                _MIN_SAMPLES,
            )
        try:
            import numpy as np

            losses = np.array([-r for r in returns], dtype=float)
            var_conf = float(np.quantile(losses, confidence, method="linear"))
            tail_conf = losses[losses >= var_conf]
            cvar_conf = float(tail_conf.mean()) if tail_conf.size > 0 else var_conf
            var_95 = float(np.quantile(losses, 0.95, method="linear"))
            var_99 = float(np.quantile(losses, 0.99, method="linear"))
            tail_95 = losses[losses >= var_95]
            tail_99 = losses[losses >= var_99]
            cvar_95 = float(tail_95.mean()) if tail_95.size > 0 else var_95
            cvar_99 = float(tail_99.mean()) if tail_99.size > 0 else var_99
        except ImportError:
            logger.warning("numpy unavailable; falling back to sorted-list quantile calculation")
            sorted_losses = sorted(-r for r in returns)
            n_losses = len(sorted_losses)

            def _quantile(sorted_vals: list[float], q: float) -> float:
                if not sorted_vals:
                    return 0.0
                pos = q * (n_losses - 1)
                lo = int(math.floor(pos))
                hi = int(math.ceil(pos))
                if lo == hi:
                    return sorted_vals[lo]
                frac = pos - lo
                return sorted_vals[lo] * (1 - frac) + sorted_losses[hi] * frac

            var_conf = _quantile(sorted_losses, confidence)
            tail_conf = [v for v in sorted_losses if v >= var_conf]
            cvar_conf = sum(tail_conf) / len(tail_conf) if tail_conf else var_conf
            var_95 = _quantile(sorted_losses, 0.95)
            var_99 = _quantile(sorted_losses, 0.99)
            tail_95 = [v for v in sorted_losses if v >= var_95]
            tail_99 = [v for v in sorted_losses if v >= var_99]
            cvar_95 = sum(tail_95) / len(tail_95) if tail_95 else var_95
            cvar_99 = sum(tail_99) / len(tail_99) if tail_99 else var_99
        return VaRResult(
            var_95=round(var_95 * portfolio_value, 2),
            var_99=round(var_99 * portfolio_value, 2),
            cvar_95=round(cvar_95 * portfolio_value, 2),
            cvar_99=round(cvar_99 * portfolio_value, 2),
            expected_shortfall=round(cvar_conf * portfolio_value, 2),
            simulations=n,
            portfolio_value=portfolio_value,
            confidence=confidence,
        )

    @staticmethod
    def monte_carlo_var(
        portfolio_value: float, mu: float, sigma: float, days: int = 252, simulations: int = 10000
    ) -> VaRResult:
        returns = [random.gauss(mu / 252, sigma / math.sqrt(252)) for _ in range(simulations)]
        return RiskModelingEngine.calculate_var(returns, portfolio_value)

    @staticmethod
    def stress_test_scenarios(
        positions: list[dict] | None = None,
        scenarios: list[dict] | None = None,
    ) -> list[StressTestResult]:
        base = [
            StressTestResult(
                scenario="利率上升200bp",
                impact=-0.15,
                probability="medium",
                affected_factors=["债券价格", "贷款成本", "净息差"],
                mitigations=["利率互换对冲", "缩短久期"],
            ),
            StressTestResult(
                scenario="股市暴跌30%",
                impact=-0.25,
                probability="low",
                affected_factors=["权益投资", "基金净值", "交易收入"],
                mitigations=["降低权益敞口", "增持防御板块"],
            ),
            StressTestResult(
                scenario="信用利差扩大",
                impact=-0.10,
                probability="medium",
                affected_factors=["信用债", "贷款质量", "CDS"],
                mitigations=["分散信用敞口", "增持高评级债"],
            ),
        ]
        if scenarios:
            for s in scenarios:
                if isinstance(s, StressTestResult):
                    base.append(s)
                elif isinstance(s, dict):
                    base.append(
                        StressTestResult(
                            scenario=str(s.get("scenario", "")),
                            impact=float(s.get("impact", 0.0) or 0.0),
                            probability=str(s.get("probability", "low")),
                            affected_factors=list(s.get("affected_factors", []) or []),
                            mitigations=list(s.get("mitigations", []) or []),
                        )
                    )
        if positions:
            total_value = 0.0
            position_values: list[float] = []
            for p in positions:
                pv = float(p.get("value", p.get("market_value", 0)) or 0)
                position_values.append(pv)
                total_value += pv
            for r in base:
                scenario_pct = r.impact
                if total_value > 0:
                    aggregate_impact = 0.0
                    for pv in position_values:
                        aggregate_impact += scenario_pct * pv
                    r.impact = round(aggregate_impact, 4)
                else:
                    logger.warning(
                        "stress_test_scenarios: positions provided but total value is 0; scenario='%s' impact left as pct",
                        r.scenario,
                    )
            logger.info(
                "stress_test_scenarios applied %d positions (total_value=%.2f) to %d scenarios",
                len(positions),
                total_value,
                len(base),
            )
        return base
