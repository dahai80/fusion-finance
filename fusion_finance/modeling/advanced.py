"""高级财务模型 — LBO、DDM、Merger Model、APV。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..ai_client import MLXClient

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
    ebitda: List[float] = field(default_factory=list)
    irr: float = 0.0
    moic: float = 0.0
    assumptions: Dict[str, Any] = field(default_factory=dict)

    def calculate(self) -> Dict[str, float]:
        if not self.ebitda:
            return {"error": "请先输入EBITDA预测"}
        debt = self.purchase_price * self.debt_pct
        equity = self.purchase_price * self.equity_pct
        exit_ev = self.ebitda[-1] * self.exit_multiple
        debt_repayment = debt * 0.2 * self.exit_year
        exit_equity = exit_ev - (debt - debt_repayment)
        self.moic = exit_equity / equity if equity else 0
        self.irr = (self.moic ** (1/self.exit_year) - 1) * 100 if self.exit_year > 0 else 0
        return {"purchase_price": self.purchase_price, "debt": round(debt, 2), "equity": round(equity, 2),
                "exit_ev": round(exit_ev, 2), "exit_equity": round(exit_equity, 2),
                "moic": round(self.moic, 2), "irr": round(self.irr, 1)}


@dataclass
class DDMModel:
    """DDM 股利贴现模型。"""
    company: str = ""
    current_dividend: float = 0.0
    growth_rate: float = 0.05
    required_return: float = 0.10
    fair_value: float = 0.0

    def calculate(self) -> Dict[str, float]:
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
    acc_eps: float = 0.0
    diluted_eps: float = 0.0
    accretion: float = 0.0

    def calculate(self) -> Dict[str, float]:
        offer_price = self.target_price * (1 + self.premium)
        if self.acquirer_price and offer_price:
            self.acc_eps = self.acquirer_price * 0.01
            self.diluted_eps = offer_price * 0.008
            self.accretion = (self.acc_eps - self.diluted_eps) / self.diluted_eps * 100
        return {"offer_price": round(offer_price, 2), "premium": self.premium * 100,
                "acc_eps": round(self.acc_eps, 4), "diluted_eps": round(self.diluted_eps, 4),
                "accretion": round(self.accretion, 1)}


class AdvancedModelingEngine:
    def __init__(self, mlx: Optional[MLXClient] = None):
        self.mlx = mlx or MLXClient()

    async def build_lbo(self, company: str, ebitda: List[float], assumptions: Optional[Dict] = None) -> LBOModel:
        prompt = f"""为{company}构建LBO杠杆收购模型。

EBITDA预测: {ebitda}
假设: {json.dumps(assumptions or {})}

返回JSON: {{"purchase_price": 收购价, "debt_pct": 债务比例, "exit_multiple": 退出倍数, "interest_rate": 利率, "assumptions": {{"key_drivers": []}} }}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位资深并购分析师，精通LBO建模。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            data = self._parse_json(response)
            if data:
                model = LBOModel(company=company, ebitda=ebitda,
                    purchase_price=data.get("purchase_price", sum(ebitda) * 8),
                    debt_pct=data.get("debt_pct", 0.6),
                    exit_multiple=data.get("exit_multiple", 10.0),
                    interest_rate=data.get("interest_rate", 0.05),
                    assumptions=data.get("assumptions", {}))
                model.calculate()
                return model
        except Exception as e:
            logger.error(f"LBO失败: {e}")
        model = LBOModel(company=company, ebitda=ebitda, purchase_price=sum(ebitda) * 8)
        model.calculate()
        return model

    def _parse_json(self, text: str) -> Any:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None