"""高级财务模型 — LBO、DDM、Merger Model、APV。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ..ai_client import MLXClient
from ..utils.parse_json import parse_json

logger = logging.getLogger(__name__)


@dataclass
class LBOModel:
    """LBO 杠杆收购模型。"""

    company: str = ""
    purchase_price: float = 0.0
    debt_pct: float = 0.6
    equity_pct: float = 0.4
    interest_rate: float = 0.05
    exit_year: int = 5
    exit_multiple: float = 10.0
    ebitda: list[float] = field(default_factory=list)
    irr: float = 0.0
    moic: float = 0.0
    assumptions: dict[str, Any] = field(default_factory=dict)
    ai_status: str = "success"

    def calculate(self) -> dict[str, float]:
        if not self.ebitda:
            return {"error": "请先输入EBITDA预测"}
        if self.exit_year <= 0:
            logger.error("LBO exit_year must be positive: %s", self.exit_year)
            return {"error": "exit_year must be positive"}
        debt = self.purchase_price * self.debt_pct
        equity = self.purchase_price * self.equity_pct
        if equity <= 0:
            logger.error("LBO equity contribution must be positive: %s", equity)
            return {"error": "equity contribution must be positive"}
        exit_ev = self.ebitda[-1] * self.exit_multiple
        annual_repayment = debt / self.exit_year
        remaining_debt = debt
        total_interest = 0.0
        for _ in range(self.exit_year):
            interest = remaining_debt * self.interest_rate
            total_interest += interest
            repayment = min(annual_repayment, remaining_debt)
            remaining_debt -= repayment
        exit_equity = exit_ev - remaining_debt - total_interest
        self.moic = exit_equity / equity
        if self.moic <= 0:
            logger.warning("LBO non-positive MOIC=%.4f, IRR not meaningful", self.moic)
            self.irr = float("-inf")
        else:
            self.irr = (self.moic ** (1 / self.exit_year) - 1) * 100
        return {
            "purchase_price": self.purchase_price,
            "debt": round(debt, 2),
            "equity": round(equity, 2),
            "exit_ev": round(exit_ev, 2),
            "total_interest": round(total_interest, 2),
            "exit_equity": round(exit_equity, 2),
            "moic": round(self.moic, 2),
            "irr": round(self.irr, 1) if self.irr != float("-inf") else float("-inf"),
        }


@dataclass
class DDMModel:
    """DDM 股利贴现模型。"""

    company: str = ""
    current_dividend: float = 0.0
    growth_rate: float = 0.05
    required_return: float = 0.10
    fair_value: float = 0.0

    def calculate(self) -> dict[str, float]:
        if self.required_return <= self.growth_rate:
            return {"error": "必要回报率必须大于增长率"}
        next_div = self.current_dividend * (1 + self.growth_rate)
        self.fair_value = next_div / (self.required_return - self.growth_rate)
        return {"next_dividend": round(next_div, 4), "fair_value": round(self.fair_value, 2)}


@dataclass
class MergerModel:
    """并购模型。"""

    acquirer: str = ""
    target: str = ""
    acquirer_price: float = 0.0
    target_price: float = 0.0
    premium: float = 0.3
    acquirer_shares: float = 0.0
    target_shares: float = 0.0
    acquirer_net_income: float = 0.0
    target_net_income: float = 0.0
    cash_consideration_pct: float = 0.0
    acc_eps: float = 0.0
    diluted_eps: float = 0.0
    accretion: float = 0.0

    def calculate(self) -> dict[str, float]:
        offer_price = self.target_price * (1 + self.premium)
        if self.acquirer_shares <= 0 or self.target_shares <= 0:
            logger.error(
                "MergerModel requires shares_outstanding for both parties: acquirer=%s target=%s",
                self.acquirer_shares,
                self.target_shares,
            )
            return {
                "error": "merger model requires shares_outstanding and net_income for both parties",
                "offer_price": round(offer_price, 2),
                "premium": self.premium * 100,
            }
        standalone_eps = self.acquirer_net_income / self.acquirer_shares
        deal_value = offer_price * self.target_shares
        new_shares_issued = (
            deal_value * (1 - self.cash_consideration_pct) / self.acquirer_price if self.acquirer_price > 0 else 0
        )
        pro_forma_shares = self.acquirer_shares + new_shares_issued
        pro_forma_net_income = self.acquirer_net_income + self.target_net_income
        self.acc_eps = standalone_eps
        self.diluted_eps = pro_forma_net_income / pro_forma_shares if pro_forma_shares > 0 else 0.0
        if self.acc_eps > 0:
            self.accretion = (self.diluted_eps - self.acc_eps) / self.acc_eps * 100
        else:
            self.accretion = 0.0
        return {
            "offer_price": round(offer_price, 2),
            "premium": self.premium * 100,
            "standalone_eps": round(standalone_eps, 4),
            "pro_forma_eps": round(self.diluted_eps, 4),
            "accretion": round(self.accretion, 1),
        }


class AdvancedModelingEngine:
    def __init__(self, mlx: MLXClient | None = None):
        self.mlx = mlx or MLXClient()

    async def build_lbo(self, company: str, ebitda: list[float], assumptions: dict | None = None) -> LBOModel:
        prompt = f"""为{company}构建LBO杠杆收购模型。

EBITDA预测: {ebitda}
假设: {json.dumps(assumptions or {})}

返回JSON: {{"purchase_price": 收购价, "debt_pct": 债务比例, "exit_multiple": 退出倍数, "interest_rate": 利率, "assumptions": {{"key_drivers": []}} }}"""
        try:
            response = await self.mlx.chat(
                [
                    {"role": "system", "content": "你是一位资深并购分析师，精通LBO建模。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            data = parse_json(response)
            if data:
                model = LBOModel(
                    company=company,
                    ebitda=ebitda,
                    purchase_price=data.get("purchase_price", sum(ebitda) * 8),
                    debt_pct=data.get("debt_pct", 0.6),
                    exit_multiple=data.get("exit_multiple", 10.0),
                    interest_rate=data.get("interest_rate", 0.05),
                    assumptions=data.get("assumptions", {}),
                )
                model.calculate()
                return model
        except Exception as e:
            logger.error(f"LBO失败: {e}")
        model = LBOModel(company=company, ebitda=ebitda, purchase_price=sum(ebitda) * 8)
        model.calculate()
        model.ai_status = "fallback"
        logger.warning("build_lbo: AI failed, returning pure-math fallback model")
        return model
