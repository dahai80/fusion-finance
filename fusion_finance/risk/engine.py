"""风控合规引擎 — KYC、信用评分、合规审查、审计日志。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..ai_client import MLXClient

logger = logging.getLogger(__name__)


@dataclass
class KYCCheck:
    entity: str = ""
    risk_level: str = "medium"
    risk_score: float = 50.0
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CreditAssessment:
    entity: str = ""
    credit_score: float = 0.0
    rating: str = "BBB"
    max_credit_line: float = 0.0
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)


class RiskComplianceEngine:
    def __init__(self, mlx: Optional[MLXClient] = None):
        self.mlx = mlx or MLXClient()

    async def kyc_screening(self, entity: str, jurisdiction: str = "CN") -> KYCCheck:
        prompt = f"""对{entity}({jurisdiction})进行KYC尽职调查。

返回JSON: {{"risk_level": "low/medium/high", "risk_score": 0-100, "findings": ["发现项"], "recommendations": ["建议"]}}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位合规分析师，精通KYC尽调和反洗钱。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            data = self._parse_json(response)
            if data:
                return KYCCheck(
                    entity=entity, risk_level=data.get("risk_level", "medium"),
                    risk_score=data.get("risk_score", 50),
                    findings=data.get("findings", []),
                    recommendations=data.get("recommendations", []),
                )
        except Exception as e:
            logger.error(f"KYC失败: {e}")
        return KYCCheck(entity=entity)

    async def credit_assessment(self, entity: str, financials: Dict[str, float]) -> CreditAssessment:
        prompt = f"""评估{entity}的信用状况。

财务数据: {json.dumps(financials)}

返回JSON: {{"credit_score": 0-100, "rating": "AAA/AA/A/BBB/BB/B/CCC", "max_credit_line": 建议授信额度, "strengths": ["信用优势"], "concerns": ["信用风险"]}}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位信用分析师，精通企业信用评估。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            data = self._parse_json(response)
            if data:
                return CreditAssessment(
                    entity=entity, credit_score=data.get("credit_score", 0),
                    rating=data.get("rating", "BBB"),
                    max_credit_line=data.get("max_credit_line", 0),
                    strengths=data.get("strengths", []),
                    concerns=data.get("concerns", []),
                )
        except Exception as e:
            logger.error(f"信用评估失败: {e}")
        return CreditAssessment(entity=entity)

    async def compliance_check(self, contract: str, regulations: str = "中国公司法") -> Dict[str, Any]:
        prompt = f"""审查以下合同是否符合{regulations}。

合同内容: {contract[:2000]}

返回JSON: {{"compliant": true/false, "issues": [{{"clause": "条款", "risk": "high/medium/low", "description": "问题描述", "suggestion": "修改建议"}}], "overall_risk": "low/medium/high", "summary": "审查总结"}}"""
        try:
            response = await self.mlx.chat([
                {"role": "system", "content": "你是一位资深法务合规专家，精通合同审查。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1)
            return self._parse_json(response) or {"compliant": True}
        except Exception as exc:
            return {"error": str(exc)}

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