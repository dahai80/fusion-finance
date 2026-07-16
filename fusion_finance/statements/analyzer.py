"""财报分析系统 — 三大报表解析、勾稽校验、财务指标提取。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..ai_client import MLXClient

logger = logging.getLogger(__name__)


@dataclass
class FinancialStatement:
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
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class FinancialAnalysis:
    company: str = ""
    period: str = ""
    revenue_growth: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    roe: float = 0.0
    roa: float = 0.0
    debt_ratio: float = 0.0
    current_ratio: float = 0.0
    pe_ratio: float = 0.0
    key_findings: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


class StatementAnalyzer:
    def __init__(self, mlx: Optional[MLXClient] = None):
        self.mlx = mlx or MLXClient()

    def calculate_metrics(self, stmt: FinancialStatement) -> FinancialAnalysis:
        analysis = FinancialAnalysis(company=stmt.company, period=stmt.period)
        if stmt.revenue:
            analysis.gross_margin = round(stmt.gross_profit / stmt.revenue * 100, 2) if stmt.gross_profit else 0
            analysis.operating_margin = round(stmt.operating_income / stmt.revenue * 100, 2) if stmt.operating_income else 0
            analysis.net_margin = round(stmt.net_income / stmt.revenue * 100, 2) if stmt.net_income else 0
        if stmt.equity:
            analysis.roe = round(stmt.net_income / stmt.equity * 100, 2) if stmt.net_income else 0
        if stmt.total_assets:
            analysis.roa = round(stmt.net_income / stmt.total_assets * 100, 2) if stmt.net_income else 0
            analysis.debt_ratio = round(stmt.total_liabilities / stmt.total_assets * 100, 2) if stmt.total_liabilities else 0
        return analysis

    async def analyze_statements(self, company: str, data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""分析{company}的财务数据并生成分析报告。

财务数据: {json.dumps(data, ensure_ascii=False)}

返回JSON: {{"revenue_growth": 收入增长率, "key_metrics": {{"毛利率": "分析", "净利率": "分析"}}, "strengths": ["财务优势"], "weaknesses": ["财务风险"], "recommendations": ["建议"], "quality_score": "财务质量评分(A/B/C/D)"}}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位资深财务分析师，精通财务报表分析。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            return self._parse_json(response) or {"company": company}
        except Exception as e:
            return {"error": str(e)}

    def validate_balance_sheet(self, statements: List[FinancialStatement]) -> List[str]:
        issues = []
        for stmt in statements:
            if stmt.total_assets and stmt.total_liabilities is not None and stmt.equity is not None:
                diff = abs(stmt.total_assets - stmt.total_liabilities - stmt.equity)
                if diff > 0.01 * stmt.total_assets:
                    issues.append(f"{stmt.period}: 资产负债表不平衡")
        return issues

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