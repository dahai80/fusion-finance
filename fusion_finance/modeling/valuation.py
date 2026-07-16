"""高级估值模型 — APV、EVA、RI、LBO 进阶。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class APVModel:
    """APV 调整现值模型 — 区分业务价值与税盾价值。"""
    company: str = ""
    unlevered_fcf: List[float] = field(default_factory=list)
    unlevered_cost: float = 0.10
    debt: float = 0.0
    tax_rate: float = 0.25
    debt_cost: float = 0.05
    terminal_growth: float = 0.03
    enterprise_value: float = 0.0
    tax_shield_value: float = 0.0

    def calculate(self) -> Dict[str, float]:
        if not self.unlevered_fcf:
            return {"error": "请先输入无杠杆自由现金流"}
        pv_fcf = sum(self.unlevered_fcf[i] / (1 + self.unlevered_cost) ** (i + 1) for i in range(len(self.unlevered_fcf)))
        tv = self.unlevered_fcf[-1] * (1 + self.terminal_growth) / (self.unlevered_cost - self.terminal_growth)
        pv_tv = tv / (1 + self.unlevered_cost) ** len(self.unlevered_fcf)
        self.tax_shield_value = self.debt * self.tax_rate
        self.enterprise_value = pv_fcf + pv_tv + self.tax_shield_value
        return {"pv_fcf": round(pv_fcf, 2), "pv_terminal": round(pv_tv, 2),
                "tax_shield": round(self.tax_shield_value, 2),
                "enterprise_value": round(self.enterprise_value, 2)}


@dataclass
class EVAModel:
    """EVA 经济增加值模型 — 衡量真实经济利润。"""
    company: str = ""
    nopat: List[float] = field(default_factory=list)
    invested_capital: List[float] = field(default_factory=list)
    wacc: float = 0.10
    eva_values: List[float] = field(default_factory=list)
    total_eva: float = 0.0

    def calculate(self) -> Dict[str, Any]:
        if not self.nopat or not self.invested_capital:
            return {"error": "请先输入NOPAT和投入资本"}
        self.eva_values = []
        for i in range(min(len(self.nopat), len(self.invested_capital))):
            charge = self.invested_capital[i] * self.wacc
            eva = self.nopat[i] - charge
            self.eva_values.append(round(eva, 2))
        self.total_eva = round(sum(self.eva_values), 2)
        return {"eva_values": self.eva_values, "total_eva": self.total_eva,
                "avg_eva": round(self.total_eva / len(self.eva_values), 2) if self.eva_values else 0}


@dataclass
class RIModel:
    """RI 剩余收益模型 — 用于股权估值。"""
    company: str = ""
    book_value: float = 0.0
    net_income: List[float] = field(default_factory=list)
    cost_of_equity: float = 0.12
    residual_income: List[float] = field(default_factory=list)
    fair_value: float = 0.0

    def calculate(self) -> Dict[str, float]:
        if not self.net_income:
            return {"error": "请先输入净利润预测"}
        self.residual_income = []
        bv = self.book_value
        for ni in self.net_income:
            normal = bv * self.cost_of_equity
            ri = ni - normal
            self.residual_income.append(round(ri, 2))
            bv = bv + ni * 0.6
        pv_ri = sum(self.residual_income[i] / (1 + self.cost_of_equity) ** (i + 1) for i in range(len(self.residual_income)))
        self.fair_value = self.book_value + pv_ri
        return {"book_value": self.book_value, "pv_ri": round(pv_ri, 2),
                "fair_value": round(self.fair_value, 2),
                "residual_income": self.residual_income}