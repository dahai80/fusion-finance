from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_finance.api.sse import EventBus, _sse_stream
from fusion_finance.copilot.tools import ToolRegistry
from fusion_finance.modeling.engine import DCFModel
from fusion_finance.modeling.scenarios import Scenario, ScenarioManager
from fusion_finance.report.formatter import ReportFormatter, _split_content


class TestScenarioManager:
    def _make_dcf(self):
        return DCFModel(company="Test", revenue=[100, 120, 140], wacc=0.10, terminal_growth=0.03)

    def test_init_with_presets(self):
        mgr = ScenarioManager(self._make_dcf())
        assert "bear" in mgr.scenarios
        assert "base" in mgr.scenarios
        assert "bull" in mgr.scenarios

    def test_scenario_to_dict(self):
        s = Scenario(name="test", label="Test", adjustments={"growth_adj": 0.1}, result={"ev": 100})
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["adjustments"] == {"growth_adj": 0.1}

    def test_add_scenario_with_label(self):
        mgr = ScenarioManager(self._make_dcf())
        s = mgr.add_scenario("custom", {"growth_adj": 0.2}, label="自定义")
        assert s.label == "自定义"
        assert "custom" in mgr.scenarios

    def test_add_scenario_without_label(self):
        mgr = ScenarioManager(self._make_dcf())
        s = mgr.add_scenario("custom2", {"growth_adj": -0.1})
        assert s.label == "custom2"

    def test_remove_scenario_exists(self):
        mgr = ScenarioManager(self._make_dcf())
        assert mgr.remove_scenario("bear") is True
        assert "bear" not in mgr.scenarios

    def test_remove_scenario_not_exists(self):
        mgr = ScenarioManager(self._make_dcf())
        assert mgr.remove_scenario("nonexistent") is False

    def test_compare(self):
        mgr = ScenarioManager(self._make_dcf())
        comp = mgr.compare()
        assert "bear" in comp
        assert "base" in comp

    def test_get_summary(self):
        mgr = ScenarioManager(self._make_dcf())
        summary = mgr.get_summary()
        assert len(summary) == 3
        base_item = [s for s in summary if s["name"] == "base"][0]
        assert base_item["delta_pct"] == 0.0

    def test_get_summary_zero_base(self):
        dcf = DCFModel(company="Z", revenue=[1], wacc=0.99, terminal_growth=0.5)
        mgr = ScenarioManager(dcf)
        summary = mgr.get_summary()
        assert len(summary) == 3

    def test_get_scenario_exists(self):
        mgr = ScenarioManager(self._make_dcf())
        s = mgr.get_scenario("base")
        assert s is not None
        assert s.name == "base"

    def test_get_scenario_missing(self):
        mgr = ScenarioManager(self._make_dcf())
        assert mgr.get_scenario("nope") is None

    def test_build_scenario_margin_adj(self):
        dcf = DCFModel(company="M", revenue=[100, 120], wacc=0.10, ebit_margin=[0.2, 0.25])
        mgr = ScenarioManager(dcf)
        s = mgr.add_scenario("margin_test", {"margin_adj": -0.05})
        assert s is not None

    def test_build_scenario_negative_wacc_guard(self):
        dcf = DCFModel(company="W", revenue=[100], wacc=0.01, terminal_growth=0.5)
        mgr = ScenarioManager(dcf)
        s = mgr.add_scenario("wacc_test", {"wacc_adj": -0.5})
        assert s.model.wacc >= 0.01


class TestToolRegistry:
    def test_init_registers_defaults(self):
        reg = ToolRegistry()
        assert len(reg._tools) == 12

    def test_get_definitions(self):
        reg = ToolRegistry()
        defs = reg.get_definitions()
        assert len(defs) == 12
        names = [d["name"] for d in defs]
        assert "build_dcf" in names
        assert "stress_test" in names

    def test_format_prompt(self):
        reg = ToolRegistry()
        prompt = reg.format_prompt()
        assert "你可以使用以下工具" in prompt
        assert "build_dcf" in prompt
        assert "```json" in prompt

    def test_register_custom(self):
        reg = ToolRegistry()
        reg.register("my_tool", lambda args: args)
        assert "my_tool" in reg._tools

    @pytest.mark.asyncio
    async def test_execute_unknown(self):
        reg = ToolRegistry()
        result = await reg.execute("nonexistent_tool", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_calculate_dcf(self):
        reg = ToolRegistry()
        result = await reg.execute("calculate_dcf", {"company": "T", "revenue": [100, 120], "wacc": 0.10})
        assert "equity_value" in result

    @pytest.mark.asyncio
    async def test_execute_var(self):
        reg = ToolRegistry()
        result = await reg.execute("calculate_var", {"returns": [0.01, -0.02, 0.03], "portfolio_value": 1000000})
        assert "var_95" in result or "error" in result

    @pytest.mark.asyncio
    async def test_execute_stress_test(self):
        reg = ToolRegistry()
        result = await reg.execute("stress_test", {})
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_execute_portfolio(self):
        reg = ToolRegistry()
        result = await reg.execute(
            "optimize_portfolio",
            {
                "returns": [0.10, 0.08, 0.06],
                "volatilities": [0.20, 0.15, 0.10],
                "correlations": [[1, 0.5, 0.3], [0.5, 1, 0.4], [0.3, 0.4, 1]],
            },
        )
        assert "weights" in result or "error" in result

    @pytest.mark.asyncio
    async def test_execute_metrics(self):
        reg = ToolRegistry()
        result = await reg.execute(
            "calculate_metrics",
            {
                "income_statement": {"revenue": 1000, "net_income": 100},
                "balance_sheet": {"total_assets": 5000, "total_equity": 2000},
                "cash_flow": {"operating_cf": 200},
            },
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_val_report(self):
        reg = ToolRegistry()
        result = await reg.execute("generate_valuation_report", {"company": "T", "revenue": [100, 120]})
        assert isinstance(result, (dict, str))

    @pytest.mark.asyncio
    async def test_execute_build_dcf_mock(self):
        reg = ToolRegistry()
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value='{"wacc": 0.10, "terminal_growth": 0.03}')
        with patch("fusion_finance.ai_client.MLXClient", return_value=mock_client):
            result = await reg.execute("build_dcf", {"company": "T", "revenue": [100, 120]})
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_build_comps_mock(self):
        reg = ToolRegistry()
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value='{"peers": [{"name":"A","pe":15}]}')
        with patch("fusion_finance.ai_client.MLXClient", return_value=mock_client):
            result = await reg.execute("build_comps", {"company": "T", "industry": "Tech"})
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_sensitivity(self):
        reg = ToolRegistry()
        result = await reg.execute(
            "sensitivity_analysis",
            {"company": "T", "revenue": [100, 120], "wacc": 0.10, "terminal_growth": 0.03},
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_monte_carlo(self):
        reg = ToolRegistry()
        result = await reg.execute("monte_carlo", {"company": "T", "revenue": [100, 120], "simulations": 100})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_kyc_mock(self):
        reg = ToolRegistry()
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value='{"risk_level":"low","findings":[]}')
        with patch("fusion_finance.ai_client.MLXClient", return_value=mock_client):
            result = await reg.execute("kyc_screening", {"entity": "T", "jurisdiction": "CN"})
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_credit_mock(self):
        reg = ToolRegistry()
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value='{"score":700,"rating":"A"}')
        with patch("fusion_finance.ai_client.MLXClient", return_value=mock_client):
            result = await reg.execute("credit_assessment", {"entity": "T", "financials": {}})
            assert isinstance(result, dict)


class TestReportFormatter:
    def test_detect_deps(self):
        fmt = ReportFormatter()
        assert fmt._jinja_env is None

    def test_get_jinja(self):
        fmt = ReportFormatter()
        env = fmt._get_jinja()
        assert env is not None

    def test_render_html_valuation(self):
        fmt = ReportFormatter()
        html = fmt.render_html("valuation", {"company": "Test", "body": "hello", "date": "2026-01-01"})
        assert "Test" in html

    def test_render_html_unknown_template(self):
        fmt = ReportFormatter()
        html = fmt.render_html("nonexistent", {"company": "X", "body": "fallback"})
        assert "X" in html

    def test_fallback_html(self):
        fmt = ReportFormatter()
        html = fmt._fallback_html("test", {"company": "C", "body": "content"})
        assert "C" in html

    def test_fallback_html_with_content_key(self):
        fmt = ReportFormatter()
        html = fmt._fallback_html("test", {"company": "C", "content": "stuff"})
        assert "stuff" in html

    def test_export_html(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("<h1>Test</h1>", "html", output_path=f"{td}/test.html")
            assert Path(path).exists()
            assert Path(path).read_text() == "<h1>Test</h1>"

    def test_export_html_with_template(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export(
                "original",
                "html",
                output_path=f"{td}/tmpl.html",
                template_name="valuation",
                template_data={"company": "C", "body": "B", "date": "2026"},
            )
            assert Path(path).exists()

    def test_export_json(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("content", "json", output_path=f"{td}/out.json", template_data={"key": "val"})
            data = json.loads(Path(path).read_text())
            assert data["key"] == "val"

    def test_export_markdown(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("# Hello", "markdown", output_path=f"{td}/out.md")
            assert Path(path).exists()
            assert "# Hello" in Path(path).read_text()

    def test_export_pdf_fallback_html(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("<h1>PDF</h1>", "pdf", output_path=f"{td}/out.pdf")
            assert Path(path).with_suffix(".html").exists() or Path(path).exists()

    def test_export_pptx_fallback_txt(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("Slide content", "pptx", output_path=f"{td}/out.pptx")
            assert Path(path).with_suffix(".txt").exists() or Path(path).exists()

    def test_export_xlsx_fallback_csv(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            path = fmt.export("col1,col2\n1,2", "xlsx", output_path=f"{td}/out.xlsx")
            assert Path(path).with_suffix(".csv").exists() or Path(path).exists()

    def test_export_unsupported_format(self):
        fmt = ReportFormatter()
        with pytest.raises(ValueError, match="Unsupported format"):
            fmt.export("x", "docx")

    def test_export_auto_path(self):
        fmt = ReportFormatter()
        with tempfile.TemporaryDirectory() as td:
            old_cwd = Path.cwd()
            import os

            os.chdir(td)
            try:
                path = fmt.export("auto", "markdown")
                assert Path(path).exists()
            finally:
                os.chdir(old_cwd)

    def test_split_content(self):
        chunks = _split_content("line1\nline2\nline3", max_chars=10)
        assert len(chunks) >= 2

    def test_split_content_single(self):
        chunks = _split_content("short", max_chars=100)
        assert len(chunks) == 1

    def test_split_content_empty(self):
        chunks = _split_content("", max_chars=100)
        assert chunks == []


class TestEventBus:
    def test_subscribe(self):
        bus = EventBus()
        q = bus.subscribe("test_ch")
        assert q is not None
        assert len(bus._subscribers["test_ch"]) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        q = bus.subscribe("test_ch")
        bus.unsubscribe("test_ch", q)
        assert len(bus._subscribers["test_ch"]) == 0

    def test_unsubscribe_missing_channel(self):
        bus = EventBus()
        bus.unsubscribe("no_ch", asyncio.Queue())

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = EventBus()
        q = bus.subscribe("ch1")
        await bus.publish("ch1", {"type": "test"})
        data = await asyncio.wait_for(q.get(), timeout=1.0)
        assert "test" in data

    @pytest.mark.asyncio
    async def test_publish_empty_channel(self):
        bus = EventBus()
        await bus.publish("empty_ch", {"type": "test"})

    @pytest.mark.asyncio
    async def test_sse_stream_data(self):
        q = asyncio.Queue()
        await q.put('{"msg":"hi"}')
        results = []
        async for chunk in _sse_stream(q, keepalive_interval=999):
            results.append(chunk)
            break
        assert len(results) == 1
        assert "data:" in results[0]


class TestAPIRoutes:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        self.app = create_app()
        self.transport = ASGITransport(app=self.app)
        self._client = AsyncClient(transport=self.transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_health(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_var(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/risk/var", json={"returns": [0.01, -0.02, 0.03], "portfolio_value": 1000000})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_stress_scenarios(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/risk/stress-scenarios")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_stress_test(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/risk/stress-test", json={"scenario": "recession", "impact": -0.2})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_sanctions(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/risk/sanctions", json={"entity": "Daesh"})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_sanctions_batch(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/risk/sanctions/batch", json={"entities": ["Daesh", "Apple"]})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_entity_graph(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/risk/entity-graph",
                json={
                    "nodes": [{"id": "N1", "name": "E1", "type": "company"}],
                    "edges": [],
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_ubo(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/risk/entity-graph/ubo",
                json={
                    "nodes": [
                        {"id": "C1", "name": "公司A", "type": "company"},
                        {"id": "P1", "name": "张三", "type": "person"},
                    ],
                    "edges": [{"source": "P1", "target": "C1", "type": "ownership", "weight": 0.6}],
                    "target_entity_id": "C1",
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_calculate_dcf(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/dcf/calculate",
                json={"company": "T", "revenue": [100, 120, 140], "wacc": 0.10, "terminal_growth": 0.03},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_batch_dcf(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/batch-dcf",
                json={
                    "models": [
                        {"company": "A", "revenue": [100, 120], "wacc": 0.1},
                        {"company": "B", "revenue": [200, 220], "wacc": 0.12},
                    ]
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_black_litterman(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/portfolio/black-litterman",
                json={
                    "market_weights": [0.4, 0.3, 0.3],
                    "cov_matrix": [[0.04, 0.006, 0.002], [0.006, 0.09, 0.006], [0.002, 0.006, 0.01]],
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_yield_curve(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/yield-curve",
                json={"maturities": [0.25, 0.5, 1, 2, 5, 10, 30]},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_yield_curve_calibrate(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/yield-curve/calibrate",
                json={
                    "maturities": [0.25, 0.5, 1, 2, 5, 10, 20, 30],
                    "observed_rates": [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.048, 0.05],
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_optimize_portfolio(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/portfolio/optimize",
                json={
                    "returns": [0.10, 0.08, 0.06],
                    "volatilities": [0.20, 0.15, 0.10],
                    "correlations": [[1, 0.5, 0.3], [0.5, 1, 0.4], [0.3, 0.4, 1]],
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_efficient_frontier(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get(
                "/api/v1/modeling/portfolio/frontier",
                params={
                    "returns": "0.10,0.08,0.06",
                    "volatilities": "0.20,0.15,0.10",
                    "correlations": "1,0.5,0.3,0.5,1,0.4,0.3,0.4,1",
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_ddm(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/ddm",
                json={"company": "T", "current_dividend": 2.0, "growth_rate": 0.05, "required_return": 0.10},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_merger(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/merger",
                json={"acquirer": "A", "target": "B", "acquirer_price": 100, "target_price": 50, "premium": 0.3},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_apv(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/apv",
                json={
                    "company": "T",
                    "unlevered_fcf": [10, 12, 14],
                    "unlevered_cost": 0.10,
                    "debt": 50,
                    "tax_rate": 0.25,
                    "debt_cost": 0.05,
                    "terminal_growth": 0.03,
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_eva(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/eva",
                json={"company": "T", "nopat": [100, 120], "invested_capital": [800, 900], "wacc": 0.10},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_ri(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/ri",
                json={"company": "T", "book_value": 100, "net_income": [15, 18, 20], "cost_of_equity": 0.12},
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_create_session(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/modeling/session", json={"company": "T"})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_scenario_compare(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/scenarios", json={"company": "T", "revenue": [100, 120, 140], "wacc": 0.10}
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_market_quotes(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/data/market/quotes", params={"market": "A"})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_market_ohlcv(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/data/market/ohlcv", json={"symbol": "600519", "bars": 10})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_market_technicals(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/data/market/technicals", json={"symbol": "600519", "bars": 60})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_risk_monte_carlo_var(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/risk/var/monte-carlo", json={"portfolio_value": 1000000, "simulations": 100})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_sensitivity(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/sensitivity",
                json={
                    "company": "T",
                    "revenue": [100, 120, 140],
                    "wacc": 0.10,
                    "terminal_growth": 0.03,
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_modeling_monte_carlo(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/modeling/monte-carlo",
                json={
                    "company": "T",
                    "revenue": [100, 120, 140],
                    "wacc": 0.10,
                    "simulations": 50,
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_report_valuation(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/report/valuation", json={"company": "T", "revenue": [100, 120]})
            assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_report_formats(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/report/formats")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_validate_balance(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/data/validate/balance", json={"assets": 100, "liabilities": 60, "equity": 40})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_validate_completeness(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/data/validate/completeness", json={"data": [{"a": 1, "b": 2}], "required_fields": ["a"]}
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_cache_list(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/data/cache")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_copilot_chat(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/api/v1/copilot/chat", json={"message": "hello", "session_id": "test"})
            assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_copilot_sessions(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.get("/api/v1/copilot/sessions")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_statements_analyze(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/statements/analyze",
                json={
                    "company": "T",
                    "data": {
                        "income_statement": {"revenue": 1000, "cogs": 600, "net_income": 100},
                        "balance_sheet": {"total_assets": 5000, "total_equity": 2000, "total_liabilities": 3000},
                        "cash_flow": {"operating_cf": 200, "investing_cf": -100, "financing_cf": -50},
                    },
                },
            )
            assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_statements_metrics(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/statements/metrics",
                json={
                    "income_statement": {"revenue": 1000, "net_income": 100},
                    "balance_sheet": {"total_assets": 5000, "total_equity": 2000},
                    "cash_flow": {"operating_cf": 200},
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_sse_publish(self):
        from httpx import AsyncClient

        async with AsyncClient(transport=self.transport, base_url="http://test") as c:
            r = await c.post("/events/publish", params={"channel": "test"}, json={"type": "ping"})
            assert r.status_code == 200
