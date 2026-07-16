"""报告生成器 — PitchBook、估值报告、投研报告、董事会材料。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..ai_client import MLXClient
from ..modeling.engine import DCFModel, CompsAnalysis

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, mlx: Optional[MLXClient] = None):
        self.mlx = mlx or MLXClient()

    def generate_valuation_report(self, company: str, dcf: DCFModel, comps: Optional[CompsAnalysis] = None) -> str:
        lines = [f"# {company} 估值报告", f"**生成日期**: {datetime.now().strftime('%Y-%m-%d')}", ""]
        lines.append("## DCF 估值")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 预测期现金流现值 | {dcf.calculate().get('pv_fcf', 0):,.2f} |")
        lines.append(f"| 终值 | {dcf.calculate().get('terminal_value', 0):,.2f} |")
        lines.append(f"| 企业价值 | {dcf.calculate().get('enterprise_value', 0):,.2f} |")
        lines.append(f"| 股权价值 | {dcf.calculate().get('equity_value', 0):,.2f} |")
        if dcf.target_price:
            lines.append(f"| 目标价 | {dcf.target_price:,.2f} |")
        lines.append("")
        if dcf.assumptions:
            lines.append("## 关键假设")
            for k, v in dcf.assumptions.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        if comps and comps.peers:
            lines.append("## 可比公司分析")
            lines.append("| 公司 | PE | EV/EBITDA | PS |")
            lines.append("|------|-----|-----------|-----|")
            for p in comps.peers:
                lines.append(f"| {p.get('name', '')} | {p.get('pe', 0):.1f} | {p.get('ev_ebitda', 0):.1f} | {p.get('ps', 0):.1f} |")
            lines.append("")
        lines.append("---")
        lines.append(f"*由 Fusion-Finance 于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 自动生成*")
        return "\n".join(lines)

    def generate_pitchbook(self, company: str, dcf: DCFModel, industry: str) -> str:
        lines = [f"# {company} — 投资推介材料", f"**行业**: {industry}", f"**日期**: {datetime.now().strftime('%Y-%m-%d')}", ""]
        lines.append("## 投资亮点")
        lines.append("1. 行业领先地位")
        lines.append("2. 强劲的财务表现")
        lines.append("3. 明确的增长战略")
        lines.append("")
        lines.append("## 估值概要")
        val = dcf.calculate()
        lines.append(f"- DCF 估值: {val.get('equity_value', 0):,.2f}")
        if dcf.target_price:
            lines.append(f"- 目标价: {dcf.target_price:,.2f}")
        lines.append("")
        lines.append("## 风险因素")
        lines.append("1. 市场竞争加剧")
        lines.append("2. 宏观经济不确定性")
        lines.append("3. 监管政策变化")
        lines.append("")
        lines.append("---")
        lines.append(f"*由 Fusion-Finance 自动生成 | 仅供内部参考*")
        return "\n".join(lines)

    async def generate_research_report(self, company: str, industry: str, data: Dict) -> str:
        prompt = f"""生成{company}({industry})的深度投研报告。

数据: {json.dumps(data, ensure_ascii=False)[:2000]}

格式: Markdown，包含投资逻辑、财务分析、行业展望、估值、风险提示。"""
        try:
            return await self.mlx.chat([
                {"role": "system", "content": "你是一位资深行业研究员，撰写深度投研报告。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3)
        except Exception as e:
            return f"# {company} 投研报告\n\n*报告生成失败: {e}*"

    def save_report(self, content: str, output_dir: str, filename: str = "") -> str:
        from pathlib import Path
        path = Path(output_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = path / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)