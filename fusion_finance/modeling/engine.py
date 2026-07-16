"""财务建模引擎 — DCF、可比公司分析、敏感性分析、蒙特卡洛模拟。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..ai_client import MLXClient

logger = logging.getLogger(__name__)


@dataclass
class DCFModel:
    """DCF 估值模型。"""
    company: str = ""
    forecast_years: int = 5
    revenue: List[float] = field(default_factory=list)
    ebit_margin: List[float] = field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    target_price: float = 0.0
    assumptions: Dict[str, Any] = field(default_factory=dict)

    def calculate(self) -> Dict[str, float]:
        """执行 DCF 计算。"""
        if not self.revenue:
            return {"error": "请先输入收入预测"}
        fcf = []
        for i in range(min(self.forecast_years, len(self.revenue))):
            rev = self.revenue[i]
            margin = self.ebit_margin[i] if i < len(self.ebit_margin) else (self.ebit_margin[-1] if self.ebit_margin else 0.15)
            ebit = rev * margin
            nopat = ebit * (1 - self.tax_rate)
            fcf.append(nopat)
        pv_fcf = sum(fcf[i] / (1 + self.wacc) ** (i + 1) for i in range(len(fcf)))
        tv = fcf[-1] * (1 + self.terminal_growth) / (self.wacc - self.terminal_growth) if fcf else 0
        pv_tv = tv / (1 + self.wacc) ** len(fcf)
        self.enterprise_value = pv_fcf + pv_tv
        self.equity_value = self.enterprise_value - self.net_debt
        if self.shares_outstanding > 0:
            self.target_price = self.equity_value / self.shares_outstanding
        return {
            "pv_fcf": round(pv_fcf, 2),
            "terminal_value": round(tv, 2),
            "pv_terminal": round(pv_tv, 2),
            "enterprise_value": round(self.enterprise_value, 2),
            "equity_value": round(self.equity_value, 2),
            "target_price": round(self.target_price, 2),
        }


@dataclass
class CompsAnalysis:
    """可比公司分析。"""
    company: str = ""
    peers: List[Dict[str, float]] = field(default_factory=list)
    avg_pe: float = 0.0
    avg_ev_ebitda: float = 0.0
    avg_ps: float = 0.0
    target_pe: float = 0.0
    target_ev_ebitda: float = 0.0
    implied_value: Dict[str, float] = field(default_factory=dict)


class FinancialModelingEngine:
    """财务建模引擎 — 对标 Claude Financial 的估值建模能力。"""

    def __init__(self, mlx: Optional[MLXClient] = None):
        self.mlx = mlx or MLXClient()

    async def build_dcf(
        self, company: str, revenue: List[float], assumptions: Optional[Dict] = None
    ) -> DCFModel:
        """AI 辅助构建 DCF 模型。"""
        prompt = f"""为{company}构建DCF估值模型。

收入预测: {revenue}
假设条件: {json.dumps(assumptions or {})}

返回JSON: {{"ebit_margin": [各年EBIT利润率], "tax_rate": 税率, "wacc": 加权平均资本成本, "terminal_growth": 永续增长率, "net_debt": 净债务, "shares": 总股本, "assumptions": {{"key_drivers": [], "risks": []}} }}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位资深投行分析师，精通DCF估值建模。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            data = self._parse_json(response)
            if data:
                model = DCFModel(
                    company=company, forecast_years=len(revenue),
                    revenue=revenue, assumptions=data.get("assumptions", {}),
                )
                if "ebit_margin" in data and isinstance(data["ebit_margin"], list):
                    model.ebit_margin = data["ebit_margin"]
                model.tax_rate = data.get("tax_rate", 0.25)
                model.wacc = data.get("wacc", 0.10)
                model.terminal_growth = data.get("terminal_growth", 0.03)
                model.net_debt = data.get("net_debt", 0.0)
                model.shares_outstanding = data.get("shares", 0.0)
                model.calculate()
                return model
        except Exception as e:
            logger.error(f"DCF构建失败: {e}")
        model = DCFModel(company=company, revenue=revenue)
        model.calculate()
        return model

    async def build_comps(
        self, company: str, industry: str, peers: Optional[List[str]] = None
    ) -> CompsAnalysis:
        """AI 辅助构建可比公司分析。"""
        peers_str = ", ".join(peers) if peers else "行业主要公司"
        prompt = f"""为{company}({industry})进行可比公司分析。

可比公司: {peers_str}

返回JSON: {{"peers": [{{"name": "公司名", "pe": 市盈率, "ev_ebitda": 企业价值/EBITDA, "ps": 市销率, "revenue_growth": 收入增长率, "ebitda_margin": EBITDA利润率}}], "target_pe": 目标市盈率, "target_ev_ebitda": 目标EV/EBITDA, "analysis": "分析结论"}}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位股票研究分析师，精通可比公司估值。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            data = self._parse_json(response)
            if data:
                peers_data = data.get("peers", [])
                comps = CompsAnalysis(company=company, peers=peers_data)
                if peers_data:
                    comps.avg_pe = sum(p.get("pe", 0) for p in peers_data) / len(peers_data)
                    comps.avg_ev_ebitda = sum(p.get("ev_ebitda", 0) for p in peers_data if p.get("ev_ebitda")) / max(len([p for p in peers_data if p.get("ev_ebitda")]), 1)
                    comps.avg_ps = sum(p.get("ps", 0) for p in peers_data) / len(peers_data)
                comps.target_pe = data.get("target_pe", comps.avg_pe)
                comps.target_ev_ebitda = data.get("target_ev_ebitda", comps.avg_ev_ebitda)
                return comps
        except Exception as e:
            logger.error(f"可比分析失败: {e}")
        return CompsAnalysis(company=company)

    async def sensitivity_analysis(
        self, model: DCFModel, wacc_range: List[float], growth_range: List[float]
    ) -> Dict[str, Any]:
        """敏感性分析 — 测试 WACC 和增长率对估值的影响。"""
        results = {}
        for wacc in wacc_range:
            row = {}
            for growth in growth_range:
                model.wacc = wacc
                model.terminal_growth = growth
                result = model.calculate()
                row[f"g={growth:.1%}"] = result.get("equity_value", 0)
            results[f"wacc={wacc:.1%}"] = row
        return {"matrix": results, "wacc_range": wacc_range, "growth_range": growth_range}

    async def monte_carlo(self, model: DCFModel, simulations: int = 1000) -> Dict[str, Any]:
        """蒙特卡洛模拟 — 评估估值区间。"""
        import random
        values = []
        for _ in range(simulations):
            wacc = model.wacc * (1 + random.gauss(0, 0.1))
            growth = model.terminal_growth * (1 + random.gauss(0, 0.2))
            revenue_mult = [1 + random.gauss(0, 0.05) for _ in model.revenue]
            m = DCFModel(
                company=model.company, forecast_years=model.forecast_years,
                revenue=[r * m for r, m in zip(model.revenue, revenue_mult)],
                ebit_margin=model.ebit_margin, tax_rate=model.tax_rate,
                wacc=wacc, terminal_growth=growth,
                net_debt=model.net_debt, shares_outstanding=model.shares_outstanding,
            )
            m.calculate()
            values.append(m.equity_value)
        values.sort()
        return {
            "mean": round(sum(values) / len(values), 2),
            "median": round(values[len(values)//2], 2),
            "p5": round(values[int(len(values)*0.05)], 2),
            "p25": round(values[int(len(values)*0.25)], 2),
            "p75": round(values[int(len(values)*0.75)], 2),
            "p95": round(values[int(len(values)*0.95)], 2),
            "min": round(values[0], 2),
            "max": round(values[-1], 2),
            "simulations": simulations,
        }

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