"""高级风控模型 — VaR、压力测试、情景分析。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class VaRResult:
    """VaR 计算结果。"""
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    expected_shortfall: float = 0.0
    simulations: int = 0
    portfolio_value: float = 0.0


@dataclass
class StressTestResult:
    """压力测试结果。"""
    scenario: str = ""
    impact: float = 0.0
    probability: str = "low"
    affected_factors: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)


class RiskModelingEngine:
    """高级风控引擎 — VaR、压力测试、情景分析。"""

    @staticmethod
    def calculate_var(returns: List[float], portfolio_value: float = 1_000_000, confidence: float = 0.95) -> VaRResult:
        if not returns:
            return VaRResult()
        sorted_rets = sorted(returns)
        n = len(sorted_rets)
        var_95_idx = max(0, int(n * (1 - 0.95)) - 1)
        var_99_idx = max(0, int(n * (1 - 0.99)) - 1)
        var_95 = sorted_rets[var_95_idx]
        var_99 = sorted_rets[var_99_idx]
        cvar_95 = sum(sorted_rets[:var_95_idx + 1]) / (var_95_idx + 1) if var_95_idx >= 0 else 0
        return VaRResult(
            var_95=round(var_95 * portfolio_value, 2),
            var_99=round(var_99 * portfolio_value, 2),
            cvar_95=round(cvar_95 * portfolio_value, 2),
            expected_shortfall=round(cvar_95 * portfolio_value, 2),
            simulations=n, portfolio_value=portfolio_value,
        )

    @staticmethod
    def monte_carlo_var(portfolio_value: float, mu: float, sigma: float, days: int = 252, simulations: int = 10000) -> VaRResult:
        import random
        returns = [random.gauss(mu / 252, sigma / math.sqrt(252)) for _ in range(simulations)]
        return RiskModelingEngine.calculate_var(returns, portfolio_value)

    @staticmethod
    def stress_test_scenarios() -> List[StressTestResult]:
        return [
            StressTestResult(scenario="利率上升200bp", impact=-0.15, probability="medium",
                           affected_factors=["债券价格", "贷款成本", "净息差"],
                           mitigations=["利率互换对冲", "缩短久期"]),
            StressTestResult(scenario="股市暴跌30%", impact=-0.25, probability="low",
                           affected_factors=["权益投资", "基金净值", "交易收入"],
                           mitigations=["降低权益敞口", "增持防御板块"]),
            StressTestResult(scenario="信用利差扩大", impact=-0.10, probability="medium",
                           affected_factors=["信用债", "贷款质量", "CDS"],
                           mitigations="分散信用敞口,增持高评级债"),
        ]