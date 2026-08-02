from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "build_dcf",
        "description": "AI辅助构建DCF估值模型，需要公司名和收入预测列表",
        "parameters": {"company": "公司名", "revenue": "收入预测列表"},
    },
    {
        "name": "calculate_dcf",
        "description": "纯数学DCF计算，需要完整参数",
        "parameters": {
            "company": "公司名",
            "revenue": "收入",
            "wacc": "加权平均资本成本",
            "terminal_growth": "永续增长率",
        },
    },
    {
        "name": "build_comps",
        "description": "AI辅助可比公司分析",
        "parameters": {"company": "公司名", "industry": "行业"},
    },
    {
        "name": "sensitivity_analysis",
        "description": "敏感性分析，测试WACC和增长率对估值的影响",
        "parameters": {"company": "公司名", "revenue": "收入", "wacc_range": "WACC范围", "growth_range": "增长率范围"},
    },
    {
        "name": "monte_carlo",
        "description": "蒙特卡洛模拟，评估估值区间",
        "parameters": {"company": "公司名", "revenue": "收入", "simulations": "模拟次数"},
    },
    {
        "name": "kyc_screening",
        "description": "KYC尽职调查",
        "parameters": {"entity": "实体名", "jurisdiction": "司法管辖区"},
    },
    {
        "name": "credit_assessment",
        "description": "信用评估",
        "parameters": {"entity": "实体名", "financials": "财务数据"},
    },
    {
        "name": "calculate_var",
        "description": "VaR风险价值计算",
        "parameters": {"returns": "收益率列表", "portfolio_value": "组合价值"},
    },
    {
        "name": "stress_test",
        "description": "获取预设压力测试场景",
        "parameters": {},
    },
    {
        "name": "generate_valuation_report",
        "description": "生成估值报告",
        "parameters": {"company": "公司名", "revenue": "收入列表"},
    },
    {
        "name": "calculate_metrics",
        "description": "计算财务指标",
        "parameters": {"income_statement": "利润表", "balance_sheet": "资产负债表", "cash_flow": "现金流量表"},
    },
    {
        "name": "optimize_portfolio",
        "description": "投资组合优化",
        "parameters": {"returns": "各资产收益率", "volatilities": "波动率", "correlations": "相关性矩阵"},
    },
]


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._definitions: list[dict[str, Any]] = list(TOOL_DEFINITIONS)
        self._register_defaults()

    def _register_defaults(self):
        self.register("build_dcf", self._build_dcf)
        self.register("calculate_dcf", self._calculate_dcf)
        self.register("build_comps", self._build_comps)
        self.register("sensitivity_analysis", self._sensitivity)
        self.register("monte_carlo", self._monte_carlo)
        self.register("kyc_screening", self._kyc)
        self.register("credit_assessment", self._credit)
        self.register("calculate_var", self._var)
        self.register("stress_test", self._stress_test)
        self.register("generate_valuation_report", self._val_report)
        self.register("calculate_metrics", self._metrics)
        self.register("optimize_portfolio", self._portfolio)

    def register(self, name: str, func: Callable):
        self._tools[name] = func
        logger.debug("Registered tool: %s", name)

    def get_definitions(self) -> list[dict[str, Any]]:
        return self._definitions

    def format_prompt(self) -> str:
        lines = ["你可以使用以下工具:"]
        for t in self._definitions:
            params = ", ".join(f"{k}: {v}" for k, v in t["parameters"].items())
            lines.append(f"- {t['name']}({params}): {t['description']}")
        lines.append("")
        lines.append("如果需要调用工具，请回复JSON格式:")
        lines.append("```json")
        lines.append('{"tool": "工具名", "args": {参数}}')
        lines.append("```")
        lines.append("如果不需要调用工具，直接回复用户问题。")
        return "\n".join(lines)

    async def execute(self, name: str, args: dict[str, Any]) -> Any:
        func = self._tools.get(name)
        if func is None:
            return {"error": f"未知工具: {name}"}
        try:
            result = await func(args)
            logger.info("Tool %s executed successfully", name)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return {"error": str(e)}

    async def _build_dcf(self, args: dict[str, Any]) -> Any:
        from ..ai_client import MLXClient
        from ..modeling.engine import FinancialModelingEngine

        mlx = MLXClient()
        engine = FinancialModelingEngine(mlx)
        model = await engine.build_dcf(args.get("company", ""), args.get("revenue", []))
        return asdict(model)

    async def _calculate_dcf(self, args: dict[str, Any]) -> Any:
        from ..modeling.engine import DCFModel

        model = DCFModel(
            company=args.get("company", ""),
            revenue=args.get("revenue", []),
            wacc=args.get("wacc", 0.10),
            terminal_growth=args.get("terminal_growth", 0.03),
        )
        return model.calculate()

    async def _build_comps(self, args: dict[str, Any]) -> Any:
        from ..ai_client import MLXClient
        from ..modeling.engine import FinancialModelingEngine

        mlx = MLXClient()
        engine = FinancialModelingEngine(mlx)
        comps = await engine.build_comps(args.get("company", ""), args.get("industry", ""))
        return asdict(comps)

    async def _sensitivity(self, args: dict[str, Any]) -> Any:
        from ..modeling.engine import DCFModel, FinancialModelingEngine

        model = DCFModel(
            company=args.get("company", ""),
            revenue=args.get("revenue", []),
            wacc=args.get("wacc", 0.10),
            terminal_growth=args.get("terminal_growth", 0.03),
        )
        model.calculate()
        engine = FinancialModelingEngine()
        wacc_range = args.get("wacc_range", [0.08, 0.09, 0.10, 0.11, 0.12])
        growth_range = args.get("growth_range", [0.01, 0.02, 0.03, 0.04, 0.05])
        return await engine.sensitivity_analysis(model, wacc_range, growth_range)

    async def _monte_carlo(self, args: dict[str, Any]) -> Any:
        from ..modeling.engine import DCFModel, FinancialModelingEngine

        model = DCFModel(
            company=args.get("company", ""),
            revenue=args.get("revenue", []),
        )
        model.calculate()
        engine = FinancialModelingEngine()
        return await engine.monte_carlo(model, args.get("simulations", 1000))

    async def _kyc(self, args: dict[str, Any]) -> Any:
        from ..ai_client import MLXClient
        from ..risk.engine import RiskComplianceEngine

        mlx = MLXClient()
        engine = RiskComplianceEngine(mlx)
        result = await engine.kyc_screening(args.get("entity", ""), args.get("jurisdiction", "CN"))
        return asdict(result)

    async def _credit(self, args: dict[str, Any]) -> Any:
        from ..ai_client import MLXClient
        from ..risk.engine import RiskComplianceEngine

        mlx = MLXClient()
        engine = RiskComplianceEngine(mlx)
        result = await engine.credit_assessment(args.get("entity", ""), args.get("financials", {}))
        return asdict(result)

    async def _var(self, args: dict[str, Any]) -> Any:
        from ..risk.advanced_risk import RiskModelingEngine

        result = RiskModelingEngine.calculate_var(
            args.get("returns", []),
            args.get("portfolio_value", 1_000_000),
        )
        return asdict(result)

    async def _stress_test(self, args: dict[str, Any]) -> Any:
        from ..risk.advanced_risk import RiskModelingEngine

        scenarios = RiskModelingEngine.stress_test_scenarios()
        return [asdict(s) for s in scenarios]

    async def _val_report(self, args: dict[str, Any]) -> Any:
        from ..modeling.engine import DCFModel
        from ..report.reports import ReportGenerator

        dcf = DCFModel(company=args.get("company", ""), revenue=args.get("revenue", []))
        dcf.calculate()
        generator = ReportGenerator()
        return generator.generate_valuation_report(args.get("company", ""), dcf)

    async def _metrics(self, args: dict[str, Any]) -> Any:
        from ..statements.analyzer import StatementAnalyzer

        analyzer = StatementAnalyzer()
        stmt = {
            "income_statement": args.get("income_statement", {}),
            "balance_sheet": args.get("balance_sheet", {}),
            "cash_flow": args.get("cash_flow", {}),
        }
        return analyzer.calculate_metrics(stmt)

    async def _portfolio(self, args: dict[str, Any]) -> Any:
        from ..modeling.portfolio import PortfolioOptimizer

        opt = PortfolioOptimizer(
            returns=args.get("returns", []),
            volatilities=args.get("volatilities", []),
            correlations=args.get("correlations", []),
        )
        return opt.optimize(args.get("target_return", 0.08))
