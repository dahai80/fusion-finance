from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from ..exceptions import FinanceError

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "build_dcf",
        "description": "AI辅助构建DCF估值模型，需要公司名和收入预测列表",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "revenue": {"type": "array", "items": {"type": "number"}, "description": "收入预测列表"},
            },
            "required": ["company", "revenue"],
        },
    },
    {
        "name": "calculate_dcf",
        "description": "纯数学DCF计算，需要完整参数",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "revenue": {"type": "array", "items": {"type": "number"}, "description": "收入"},
                "wacc": {"type": "number", "description": "加权平均资本成本"},
                "terminal_growth": {"type": "number", "description": "永续增长率"},
            },
            "required": ["company", "revenue"],
        },
    },
    {
        "name": "build_comps",
        "description": "AI辅助可比公司分析",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "industry": {"type": "string", "description": "行业"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "sensitivity_analysis",
        "description": "敏感性分析，测试WACC和增长率对估值的影响",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "revenue": {"type": "array", "items": {"type": "number"}, "description": "收入"},
                "wacc_range": {"type": "array", "items": {"type": "number"}, "description": "WACC范围"},
                "growth_range": {"type": "array", "items": {"type": "number"}, "description": "增长率范围"},
            },
            "required": ["company", "revenue"],
        },
    },
    {
        "name": "monte_carlo",
        "description": "蒙特卡洛模拟，评估估值区间",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "revenue": {"type": "array", "items": {"type": "number"}, "description": "收入"},
                "simulations": {"type": "integer", "description": "模拟次数"},
            },
            "required": ["company", "revenue"],
        },
    },
    {
        "name": "kyc_screening",
        "description": "KYC尽职调查",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "实体名"},
                "jurisdiction": {"type": "string", "description": "司法管辖区"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "credit_assessment",
        "description": "信用评估",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "实体名"},
                "financials": {"type": "object", "description": "财务数据"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "calculate_var",
        "description": "VaR风险价值计算",
        "parameters": {
            "type": "object",
            "properties": {
                "returns": {"type": "array", "items": {"type": "number"}, "description": "收益率列表"},
                "portfolio_value": {"type": "number", "description": "组合价值"},
            },
            "required": ["returns"],
        },
    },
    {
        "name": "stress_test",
        "description": "获取预设压力测试场景",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "generate_valuation_report",
        "description": "生成估值报告",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "公司名"},
                "revenue": {"type": "array", "items": {"type": "number"}, "description": "收入列表"},
            },
            "required": ["company", "revenue"],
        },
    },
    {
        "name": "calculate_metrics",
        "description": "计算财务指标",
        "parameters": {
            "type": "object",
            "properties": {
                "income_statement": {"type": "object", "description": "利润表"},
                "balance_sheet": {"type": "object", "description": "资产负债表"},
                "cash_flow": {"type": "object", "description": "现金流量表"},
            },
            "required": ["income_statement"],
        },
    },
    {
        "name": "optimize_portfolio",
        "description": "投资组合优化",
        "parameters": {
            "type": "object",
            "properties": {
                "returns": {"type": "array", "items": {"type": "number"}, "description": "各资产收益率"},
                "volatilities": {"type": "array", "items": {"type": "number"}, "description": "波动率"},
                "correlations": {"type": "array", "description": "相关性矩阵"},
            },
            "required": ["returns", "volatilities", "correlations"],
        },
    },
    {
        "name": "black_litterman",
        "description": "Black-Litterman模型组合优化，融合市场均衡与投资者观点",
        "parameters": {
            "type": "object",
            "properties": {
                "returns": {"type": "array", "items": {"type": "number"}, "description": "各资产收益率"},
                "volatilities": {"type": "array", "items": {"type": "number"}, "description": "波动率"},
                "correlations": {"type": "array", "description": "相关性矩阵"},
                "views": {"type": "array", "description": "投资者观点列表"},
            },
            "required": ["returns", "volatilities", "correlations"],
        },
    },
    {
        "name": "sanctions_screening",
        "description": "制裁名单筛查，支持Levenshtein模糊匹配和关键词匹配",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "实体名"},
                "threshold": {"type": "number", "description": "匹配阈值(0-1)"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "entity_resolution",
        "description": "实体关系图谱分析，支持UBO追溯和PEP扫描",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "实体名"},
                "depth": {"type": "integer", "description": "追溯深度"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "market_feed",
        "description": "模拟行情数据生成，支持A股/港股实时报价",
        "parameters": {
            "type": "object",
            "properties": {
                "market": {"type": "string", "description": "市场(A/HK)"},
            },
            "required": [],
        },
    },
    {
        "name": "bond_analysis",
        "description": "债券分析，计算久期、凸性、YTM等指标",
        "parameters": {
            "type": "object",
            "properties": {
                "face_value": {"type": "number", "description": "面值"},
                "coupon_rate": {"type": "number", "description": "票息率"},
                "years": {"type": "integer", "description": "期限"},
                "yield_to_maturity": {"type": "number", "description": "到期收益率"},
            },
            "required": [],
        },
    },
    {
        "name": "yield_curve",
        "description": "Nelson-Siegel收益率曲线校准，根据观测利率拟合参数",
        "parameters": {
            "type": "object",
            "properties": {
                "maturities": {"type": "array", "items": {"type": "number"}, "description": "期限列表"},
                "yields": {"type": "array", "items": {"type": "number"}, "description": "收益率列表"},
            },
            "required": ["maturities", "yields"],
        },
    },
]

try:
    from ..risk.entity_resolution import EntityGraph, EntityResolver

    _ENTITY_RESOLUTION_AVAILABLE = True
    logger.info("entity_resolution module loaded: EntityGraph, EntityResolver available")
except ImportError as e:
    try:
        from ..risk.entity_resolution import EntityGraph

        _ENTITY_RESOLUTION_AVAILABLE = True
        EntityResolver = None  # type: ignore[assignment]
        logger.warning("entity_resolution: EntityResolver not available, using EntityGraph only (%s)", e)
    except ImportError as e2:
        EntityGraph = None  # type: ignore[assignment]
        EntityResolver = None  # type: ignore[assignment]
        _ENTITY_RESOLUTION_AVAILABLE = False
        logger.error("entity_resolution module unavailable: %s", e2)


def _schema_to_prompt(schema: dict[str, Any]) -> str:
    props = schema.get("properties", {})
    if not props:
        return ""
    required = set(schema.get("required", []))
    parts = []
    for key, spec in props.items():
        t = spec.get("type", "any")
        desc = spec.get("description", "")
        marker = " (required)" if key in required else ""
        parts.append(f"{key}: {t}{marker} — {desc}")
    return "; ".join(parts)


class ToolRegistry:
    def __init__(self, mlx: Any = None):
        self._tools: dict[str, Callable] = {}
        self._selectable: dict[str, bool] = {}
        self._definitions: list[dict[str, Any]] = list(TOOL_DEFINITIONS)
        self._frozen = False
        self._mlx = mlx
        self._register_defaults()
        self._frozen = True

    def _get_mlx(self) -> Any:
        if self._mlx is not None:
            return self._mlx
        from ..ai_client import MLXClient

        self._mlx = MLXClient()
        logger.debug("ToolRegistry created ephemeral MLXClient for AI tools")
        return self._mlx

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

    def register(self, name: str, func: Callable, selectable: bool = True) -> None:
        if name in self._tools:
            logger.warning("Overwriting existing tool registration: %s", name)
        self._tools[name] = func
        self._selectable[name] = selectable
        if self._frozen:
            logger.warning("Registry is frozen, runtime override of tool %s may be unsafe", name)
        logger.debug("Registered tool: %s (selectable=%s)", name, selectable)

    def get_definitions(self) -> list[dict[str, Any]]:
        return [d for d in self._definitions if self._selectable.get(d["name"], True)]

    def format_prompt(self) -> str:
        lines = ["你可以使用以下工具:"]
        for t in self.get_definitions():
            params = _schema_to_prompt(t.get("parameters", {}))
            lines.append(f"- {t['name']}({params}): {t['description']}")
        lines.append("")
        lines.append("如果需要调用工具，请回复JSON格式:")
        lines.append("```json")
        lines.append('{"tool": "工具名", "args": {参数}}')
        lines.append("```")
        lines.append("如需一次调用多个独立工具，请回复批量格式:")
        lines.append("```json")
        lines.append('{"tool_calls": [{"tool": "工具名", "args": {参数}}, ...]}')
        lines.append("```")
        lines.append("如果不需要调用工具，直接回复用户问题。")
        return "\n".join(lines)

    async def execute(self, name: str, args: dict[str, Any]) -> Any:
        func = self._tools.get(name)
        if func is None:
            logger.warning("Unknown tool requested: %s", name)
            return {"error": "tool_failed", "code": "unknown_tool", "name": name}
        if not isinstance(args, dict):
            logger.warning("Tool %s args not dict: %r", name, type(args).__name__)
            return {"error": "tool_failed", "code": "invalid_args_type", "name": name}
        try:
            self._validate_args(name, args)
            result = await func(args)
            logger.info("Tool %s executed successfully", name)
            return result
        except (ValueError, TypeError) as e:
            logger.error("Tool %s input error: %s", name, e)
            return {"error": "tool_failed", "code": type(e).__name__, "name": name}
        except KeyError as e:
            logger.error("Tool %s missing key: %s", name, e)
            return {"error": "tool_failed", "code": "missing_key", "name": name, "key": str(e)}
        except FinanceError as e:
            logger.error("Tool %s finance error: %s", name, e.message)
            return {"error": "tool_failed", "code": type(e).__name__, "name": name}

    def _validate_args(self, name: str, args: dict[str, Any]) -> None:
        definition = next((d for d in self._definitions if d["name"] == name), None)
        if not definition:
            return
        schema = definition.get("parameters", {})
        required = schema.get("required", [])
        missing = [k for k in required if k not in args or args[k] is None]
        if missing:
            raise KeyError(f"missing required parameter(s): {missing}")
        props = schema.get("properties", {})
        for key, value in args.items():
            spec = props.get(key)
            if not spec:
                continue
            self._check_type(key, value, spec.get("type"))
            self._check_item_type(key, value, spec.get("items"))

    @staticmethod
    def _check_type(key: str, value: Any, expected: str | None) -> None:
        if expected is None or expected == "any":
            return
        type_map = {
            "string": (str,),
            "number": (int, float),
            "integer": (int,),
            "array": (list, tuple),
            "object": (dict,),
        }
        allowed = type_map.get(expected)
        if allowed is None:
            return
        if not isinstance(value, allowed):
            raise TypeError(f"parameter {key!r} expected {expected}, got {type(value).__name__}")

    @classmethod
    def _check_item_type(cls, key: str, value: Any, items_spec: dict[str, Any] | None) -> None:
        if not items_spec or not isinstance(value, (list, tuple)):
            return
        item_type = items_spec.get("type")
        if not item_type:
            return
        for i, item in enumerate(value):
            cls._check_type(f"{key}[{i}]", item, item_type)

    async def _build_dcf(self, args: dict[str, Any]) -> Any:
        from ..modeling.engine import FinancialModelingEngine

        mlx = self._get_mlx()
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
        from ..modeling.engine import FinancialModelingEngine

        mlx = self._get_mlx()
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
        from ..risk.engine import RiskComplianceEngine

        mlx = self._get_mlx()
        engine = RiskComplianceEngine(mlx)
        result = await engine.kyc_screening(args.get("entity", ""), args.get("jurisdiction", "CN"))
        return asdict(result)

    async def _credit(self, args: dict[str, Any]) -> Any:
        from ..risk.engine import RiskComplianceEngine

        mlx = self._get_mlx()
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
        from ..statements import FinancialStatement
        from ..statements.analyzer import StatementAnalyzer

        analyzer = StatementAnalyzer()
        income = args.get("income_statement", {}) or {}
        balance = args.get("balance_sheet", {}) or {}
        stmt = FinancialStatement(
            company=income.get("company", "Unknown"),
            revenue=income.get("revenue", 0) or 0,
            net_income=income.get("net_income", 0) or 0,
            total_assets=balance.get("total_assets", 0) or 0,
            equity=balance.get("total_equity", 0) or 0,
        )
        analysis = analyzer.calculate_metrics(stmt)
        return {
            "gross_margin": analysis.gross_margin,
            "net_margin": analysis.net_margin,
            "roe": analysis.roe,
            "roa": analysis.roa,
            "debt_ratio": analysis.debt_ratio,
        }

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
        if not _ENTITY_RESOLUTION_AVAILABLE or EntityGraph is None:
            logger.error("entity_resolution tool unavailable: module not loaded")
            return {"error": "tool_failed", "code": "module_unavailable", "name": "entity_resolution"}
        entity = args.get("entity", "")
        depth = args.get("depth", 2)
        graph = EntityGraph()
        if EntityResolver is not None:
            resolver = EntityResolver()
            graph_results = resolver.resolve(entity) if hasattr(resolver, "resolve") else []
            ubo = resolver.resolve_ubo(graph, entity) if hasattr(resolver, "resolve_ubo") else []
            pep = resolver.find_pep_connections(graph) if hasattr(resolver, "find_pep_connections") else []
            return {
                "resolved": [str(e) for e in graph_results],
                "ubo": ubo,
                "pep": pep,
            }
        parents = graph.get_parents(entity)
        children = graph.get_children(entity)
        return {
            "resolved": [entity],
            "parents": [str(p) for p in parents],
            "children": [str(c) for c in children],
            "depth": depth,
        }

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
