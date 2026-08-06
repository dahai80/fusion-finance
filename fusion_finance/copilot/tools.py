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
    {
        "name": "black_litterman",
        "description": "Black-Litterman模型组合优化，融合市场均衡与投资者观点",
        "parameters": {
            "returns": "各资产收益率",
            "volatilities": "波动率",
            "correlations": "相关性矩阵",
            "views": "投资者观点列表",
        },
    },
    {
        "name": "sanctions_screening",
        "description": "制裁名单筛查，支持Levenshtein模糊匹配和关键词匹配",
        "parameters": {"entity": "实体名", "threshold": "匹配阈值(0-1)"},
    },
    {
        "name": "entity_resolution",
        "description": "实体关系图谱分析，支持UBO追溯和PEP扫描",
        "parameters": {"entity": "实体名", "depth": "追溯深度"},
    },
    {
        "name": "market_feed",
        "description": "模拟行情数据生成，支持A股/港股实时报价",
        "parameters": {"market": "市场(A/HK)"},
    },
    {
        "name": "bond_analysis",
        "description": "债券分析，计算久期、凸性、YTM等指标",
        "parameters": {
            "face_value": "面值",
            "coupon_rate": "票息率",
            "years": "期限",
            "yield_to_maturity": "到期收益率",
        },
    },
    {
        "name": "yield_curve",
        "description": "Nelson-Siegel收益率曲线校准，根据观测利率拟合参数",
        "parameters": {"maturities": "期限列表", "yields": "收益率列表"},
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
        self.register("black_litterman", self._black_litterman)
        self.register("sanctions_screening", self._sanctions)
        self.register("entity_resolution", self._entity_resolution)
        self.register("market_feed", self._market_feed)
        self.register("bond_analysis", self._bond)
        self.register("yield_curve", self._yield_curve)

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

    async def _black_litterman(self, args: dict[str, Any]) -> Any:
        from ..modeling.portfolio import BlackLittermanOptimizer

        bl = BlackLittermanOptimizer(
            returns=args.get("returns", []),
            volatilities=args.get("volatilities", []),
            correlations=args.get("correlations", []),
        )
        return bl.optimize(args.get("views", []))

    async def _sanctions(self, args: dict[str, Any]) -> Any:
        from ..risk.sanctions import SanctionsEngine

        engine = SanctionsEngine()
        results = engine.screen(args.get("entity", ""), threshold=args.get("threshold", 0.6))
        return [asdict(r) for r in results]

    async def _entity_resolution(self, args: dict[str, Any]) -> Any:
        from ..risk.entity_resolution import EntityGraph, EntityResolver

        graph = EntityGraph()
        resolver = EntityResolver(graph)
        depth = args.get("depth", 2)
        entity = args.get("entity", "")
        graph_results = resolver.resolve(entity)
        ubo = resolver.trace_ubo(entity, max_depth=depth)
        pep = resolver.scan_pep(entity)
        return {"resolved": [str(e) for e in graph_results], "ubo": [str(u) for u in ubo], "pep": pep}

    async def _market_feed(self, args: dict[str, Any]) -> Any:
        from ..data.market_feed import MarketFeedSimulator

        sim = MarketFeedSimulator()
        market = args.get("market", "A")
        quotes = sim.generate_quotes(market=market)
        return [asdict(q) for q in quotes]

    async def _bond(self, args: dict[str, Any]) -> Any:
        from ..modeling.portfolio import Bond

        bond = Bond(
            face_value=args.get("face_value", 1000),
            coupon_rate=args.get("coupon_rate", 0.05),
            years_to_maturity=args.get("years", 5),
            yield_to_maturity=args.get("yield_to_maturity", 0.05),
        )
        return bond.calculate()

    async def _yield_curve(self, args: dict[str, Any]) -> Any:
        from ..modeling.portfolio import YieldCurve

        curve = YieldCurve()
        maturities = args.get("maturities", [])
        yields = args.get("yields", [])
        if maturities and yields:
            result = curve.calibrate(maturities, yields)
            return result
        return {"error": "需要提供maturities和yields参数"}
