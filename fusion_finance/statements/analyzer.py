"""财报分析系统 — 三大报表解析、勾稽校验、财务指标提取。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ..ai_client import MLXClient
from ..exceptions import AIClientError
from ..utils.parse_json import parse_json

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
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class FinancialAnalysis:
    company: str = ""
    period: str = ""
    revenue_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roa: float | None = None
    debt_ratio: float | None = None
    current_ratio: float | None = None
    pe_ratio: float | None = None
    key_findings: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


class StatementAnalyzer:
    def __init__(self, mlx: MLXClient | None = None):
        self.mlx = mlx or MLXClient()

    def calculate_metrics(self, stmt: FinancialStatement) -> FinancialAnalysis:
        analysis = FinancialAnalysis(company=stmt.company, period=stmt.period)
        if stmt.revenue:
            analysis.gross_margin = (
                round(stmt.gross_profit / stmt.revenue * 100, 2) if stmt.gross_profit is not None else None
            )
            analysis.operating_margin = (
                round(stmt.operating_income / stmt.revenue * 100, 2) if stmt.operating_income is not None else None
            )
            analysis.net_margin = (
                round(stmt.net_income / stmt.revenue * 100, 2) if stmt.net_income is not None else None
            )
        if stmt.equity:
            analysis.roe = round(stmt.net_income / stmt.equity * 100, 2) if stmt.net_income is not None else None
        if stmt.total_assets:
            analysis.roa = round(stmt.net_income / stmt.total_assets * 100, 2) if stmt.net_income is not None else None
            analysis.debt_ratio = (
                round(stmt.total_liabilities / stmt.total_assets * 100, 2)
                if stmt.total_liabilities is not None
                else None
            )
        logger.info(
            "calculate_metrics: company=%s period=%s gross_margin=%s net_margin=%s roe=%s",
            stmt.company,
            stmt.period,
            analysis.gross_margin,
            analysis.net_margin,
            analysis.roe,
        )
        return analysis

    async def analyze_statements(self, company: str, data: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""分析{company}的财务数据并生成分析报告。

财务数据: {json.dumps(data, ensure_ascii=False)}

返回JSON: {{"revenue_growth": 收入增长率, "key_metrics": {{"毛利率": "分析", "净利率": "分析"}}, "strengths": ["财务优势"], "weaknesses": ["财务风险"], "recommendations": ["建议"], "quality_score": "财务质量评分(A/B/C/D)"}}"""
        try:
            response = await self.mlx.chat(
                [
                    {"role": "system", "content": "你是一位资深财务分析师，精通财务报表分析。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            return parse_json(response) or {"company": company, "ai_status": "fallback"}
        except Exception as e:
            logger.error("analyze_statements AI failed: %s", e)
            raise AIClientError(message="statement analysis AI failed", detail=str(e)) from e

    def validate_balance_sheet(self, statements: list[FinancialStatement]) -> list[str]:
        issues = []
        for stmt in statements:
            if stmt.total_assets is not None and stmt.total_liabilities is not None and stmt.equity is not None:
                diff = abs(stmt.total_assets - stmt.total_liabilities - stmt.equity)
                tolerance = max(0.01, abs(stmt.total_assets) * 0.01)
                if diff > tolerance:
                    issues.append(f"{stmt.period}: 资产负债表不平衡 (diff={diff:.4f}, tolerance={tolerance:.4f})")
                    logger.warning(
                        "Balance sheet imbalance: company=%s period=%s diff=%.4f",
                        stmt.company,
                        stmt.period,
                        diff,
                    )
        return issues
