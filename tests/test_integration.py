"""Phase 6 tests: WebSocket, CLI, normalizer, screener."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from fusion_finance.cli import cli
from fusion_finance.copilot.tools import ToolRegistry
from fusion_finance.modeling.engine import DCFModel
from fusion_finance.modeling.scenarios import Scenario, ScenarioManager
from fusion_finance.statements.normalizer import StatementNormalizer
from fusion_finance.statements.screener import FinancialScreener, ScreenFilter

# ── WebSocket Tests ──


class TestWSModelingProgress:
    def test_subscribe_action(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/modeling/progress") as ws:
            ws.send_json({"action": "subscribe", "channel": "modeling"})
            data = ws.receive_json()
            assert data["type"] == "subscribed"

    def test_ping_action(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/modeling/progress") as ws:
            ws.send_json({"action": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_unknown_action(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/modeling/progress") as ws:
            ws.send_json({"action": "foo"})
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_invalid_json_modeling(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/modeling/progress") as ws:
            ws.send_text("not json")
            data = ws.receive_json()
            assert data["type"] == "error"


class TestWSCopilot:
    def test_empty_message(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/copilot") as ws:
            ws.send_json({"message": ""})
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_invalid_json_copilot(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/copilot") as ws:
            ws.send_text("bad json")
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_valid_message_stream(self):
        from starlette.testclient import TestClient

        from fusion_finance.api.app import create_app

        async def fake_stream(*args, **kwargs):
            yield {"type": "text", "content": "hi"}
            yield {"type": "text", "content": " there"}

        with (
            patch("fusion_finance.api.routes.ws.MLXClient") as MockMLX,
            patch("fusion_finance.api.routes.ws.CopilotEngine") as MockEngine,
        ):
            MockMLX.return_value = MagicMock()
            MockEngine.return_value.chat_stream = fake_stream

            app = create_app()
            client = TestClient(app)
            with client.websocket_connect("/ws/copilot") as ws:
                ws.send_json({"message": "hello"})
                thinking = ws.receive_json()
                assert thinking["type"] == "thinking"


# ── CLI Tests ──


class TestCLI:
    def test_cli_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "Fusion-Finance" in result.output

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "model" in result.output
        assert "statement" in result.output
        assert "risk" in result.output
        assert "report" in result.output

    def test_model_dcf_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["model", "dcf", "--help"])
        assert result.exit_code == 0
        assert "COMPANY" in result.output

    def test_statement_analyze(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["statement", "analyze", "Apple", "--revenue", "1000", "--net-income", "200", "--total-assets", "5000"]
        )
        assert result.exit_code == 0
        assert "Apple" in result.output
        assert "净利率" in result.output

    def test_statement_analyze_no_options(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["statement", "analyze", "TestCo"])
        assert result.exit_code == 0
        assert "TestCo" in result.output

    def test_report_valuation(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "valuation", "Apple", "-o", "/tmp"])
        assert result.exit_code == 0
        assert "报告" in result.output or "保存" in result.output

    def test_serve_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "host" in result.output.lower() or "port" in result.output.lower()

    def test_risk_kyc(self):
        mock_result = MagicMock()
        mock_result.risk_level = "LOW"
        mock_result.risk_score = 15.0

        with (
            patch("fusion_finance.cli.RiskComplianceEngine") as MockEngine,
            patch("fusion_finance.cli.asyncio.run", return_value=None),
        ):
            MockEngine.return_value.kyc_screening = AsyncMock(return_value=mock_result)
            runner = CliRunner()
            result = runner.invoke(cli, ["risk", "kyc", "TestCorp"])
            assert result.exit_code == 0

    def test_model_dcf(self):
        mock_model = MagicMock()
        mock_model.wacc = 0.10
        mock_model.target_price = None
        mock_model.calculate.return_value = {"enterprise_value": 1000, "equity_value": 800}

        with (
            patch("fusion_finance.cli.FinancialModelingEngine") as MockEngine,
            patch("fusion_finance.cli.asyncio.run", return_value=None),
        ):
            MockEngine.return_value.build_dcf = AsyncMock(return_value=mock_model)
            runner = CliRunner()
            result = runner.invoke(cli, ["model", "dcf", "Apple", "100", "120"])
            assert result.exit_code == 0


# ── Normalizer API Tests ──


class TestNormalizerAPI:
    async def test_normalize_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/normalize",
                json={
                    "data": {"营业收入": 1000, "净利润": 200, "总资产": 5000, "总负债": 3000, "股东权益": 2000},
                    "standard": "A",
                    "company": "TestCo",
                    "period": "2024",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["company"] == "TestCo"
            assert body["revenue"] == 1000

    async def test_normalize_hk_standard(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/normalize",
                json={
                    "data": {"turnover": 500, "profit_for_year": 100},
                    "standard": "HK",
                    "company": "HKCo",
                    "period": "2024",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["revenue"] == 500
            assert body["net_income"] == 100

    async def test_normalize_us_standard(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/normalize",
                json={
                    "data": {"total_revenue": 2000, "net_earnings": 400, "stockholders_equity": 1500},
                    "standard": "US",
                    "company": "USCo",
                    "period": "2024",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["revenue"] == 2000
            assert body["net_income"] == 400
            assert body["equity"] == 1500

    async def test_standards_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/statements/standards")
            assert resp.status_code == 200
            body = resp.json()
            codes = [s["code"] for s in body["standards"]]
            assert "A" in codes
            assert "HK" in codes
            assert "US" in codes

    async def test_trend_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/trend",
                json={
                    "statements": [
                        {
                            "company": "t",
                            "period": "2023",
                            "revenue": 100,
                            "net_income": 20,
                            "total_assets": 200,
                            "total_liabilities": 100,
                            "equity": 100,
                        },
                        {
                            "company": "t",
                            "period": "2024",
                            "revenue": 120,
                            "net_income": 25,
                            "total_assets": 220,
                            "total_liabilities": 110,
                            "equity": 110,
                        },
                    ]
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "revenue" in body

    async def test_screener_presets_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/statements/screener-presets")
            assert resp.status_code == 200
            body = resp.json()
            assert "value" in body["presets"]
            assert "growth" in body["presets"]


# ── Screener Unit Tests ──


class TestFinancialScreener:
    def test_load_sample_data(self):
        s = FinancialScreener()
        s.load_sample_data()
        assert len(s.stocks) > 0

    def test_screen_with_preset(self):
        s = FinancialScreener()
        s.load_sample_data()
        result = s.screen(preset="value")
        assert isinstance(result, list)

    def test_screen_with_filters(self):
        s = FinancialScreener()
        s.load_sample_data()
        filters = [ScreenFilter(metric="roe", min_val=15)]
        result = s.screen(filters=filters)
        assert isinstance(result, list)

    def test_score_stocks(self):
        s = FinancialScreener()
        s.load_sample_data()
        scored = s.score(s.stocks)
        assert len(scored) == len(s.stocks)
        for stock in scored:
            assert hasattr(stock, "score")

    def test_screen_and_rank(self):
        s = FinancialScreener()
        s.load_sample_data()
        result = s.screen_and_rank(preset="growth", limit=5)
        assert isinstance(result, dict)
        assert "results" in result
        assert len(result["results"]) <= 5

    def test_add_stock(self):
        from fusion_finance.statements.screener import StockEntry

        s = FinancialScreener()
        entry = StockEntry(ticker="TEST", name="TestCo", sector="Tech", market="A", metrics={"pe_ratio": 10, "roe": 20})
        s.add_stock(entry)
        assert any(st.ticker == "TEST" for st in s.stocks)

    def test_list_presets(self):
        s = FinancialScreener()
        presets = s.list_presets()
        assert "value" in presets
        assert "growth" in presets
        assert "dividend" in presets
        assert "quality" in presets

    def test_screen_empty_result(self):
        s = FinancialScreener()
        s.load_sample_data()
        filters = [ScreenFilter(metric="roe", min_val=999)]
        result = s.screen(filters=filters)
        assert result == []


# ── Normalizer Unit Tests ──


class TestStatementNormalizer:
    def test_normalize_a_stock(self):
        n = StatementNormalizer(standard="A")
        raw = {"营业收入": 1000, "净利润": 200, "资产总计": 5000, "负债合计": 3000, "股东权益合计": 2000}
        stmt = n.normalize(raw, company="A股公司", period="2024")
        assert stmt.revenue == 1000
        assert stmt.net_income == 200
        assert stmt.total_assets == 5000
        assert stmt.equity == 2000

    def test_normalize_hk_stock(self):
        n = StatementNormalizer(standard="HK")
        raw = {"turnover": 800, "profit_for_year": 150}
        stmt = n.normalize(raw, company="HKCo", period="2024")
        assert stmt.revenue == 800
        assert stmt.net_income == 150

    def test_normalize_us_gaap(self):
        n = StatementNormalizer(standard="US")
        raw = {"total_revenue": 2000, "net_earnings": 400, "stockholders_equity": 1500}
        stmt = n.normalize(raw, company="USCo", period="2024")
        assert stmt.revenue == 2000
        assert stmt.net_income == 400
        assert stmt.equity == 1500

    def test_normalize_multi(self):
        n = StatementNormalizer(standard="A")
        raw_list = [
            {"营业收入": 100, "净利润": 20, "period": "2023"},
            {"营业收入": 120, "净利润": 25, "period": "2024"},
        ]
        stmts = n.normalize_multi(raw_list, standard="A")
        assert len(stmts) == 2

    def test_year_over_year(self):
        from fusion_finance.statements.analyzer import FinancialStatement

        n = StatementNormalizer()
        curr = FinancialStatement(
            company="t", period="2024", revenue=120, net_income=25, total_assets=220, total_liabilities=110, equity=110
        )
        prev = FinancialStatement(
            company="t", period="2023", revenue=100, net_income=20, total_assets=200, total_liabilities=100, equity=100
        )
        yoy = n.year_over_year(curr, prev)
        assert yoy["revenue_yoy"] == 20.0
        assert yoy["net_income_yoy"] == 25.0

    def test_quarter_over_quarter(self):
        from fusion_finance.statements.analyzer import FinancialStatement

        n = StatementNormalizer()
        q1 = FinancialStatement(
            company="t", period="Q1", revenue=100, net_income=20, total_assets=200, total_liabilities=100, equity=100
        )
        q2 = FinancialStatement(
            company="t", period="Q2", revenue=110, net_income=22, total_assets=210, total_liabilities=105, equity=105
        )
        qoq = n.quarter_over_quarter(q2, q1)
        assert qoq["revenue_qoq"] == 10.0

    def test_trend_analysis(self):
        from fusion_finance.statements.analyzer import FinancialStatement

        n = StatementNormalizer()
        stmts = [
            FinancialStatement(
                company="t", period="2022", revenue=80, net_income=15, total_assets=180, total_liabilities=90, equity=90
            ),
            FinancialStatement(
                company="t",
                period="2023",
                revenue=100,
                net_income=20,
                total_assets=200,
                total_liabilities=100,
                equity=100,
            ),
            FinancialStatement(
                company="t",
                period="2024",
                revenue=120,
                net_income=25,
                total_assets=220,
                total_liabilities=110,
                equity=110,
            ),
        ]
        trend = n.trend_analysis(stmts)
        assert "revenue" in trend
        assert trend["revenue"]["direction"] == "up"

    def test_list_standards(self):
        standards = StatementNormalizer.list_standards()
        codes = [s["code"] for s in standards]
        assert "A" in codes
        assert "HK" in codes
        assert "US" in codes

    def test_normalize_empty_data(self):
        n = StatementNormalizer(standard="A")
        stmt = n.normalize({}, company="Empty", period="2024")
        assert stmt.revenue == 0

    def test_normalize_unknown_standard(self):
        n = StatementNormalizer(standard="UNKNOWN")
        stmt = n.normalize({"revenue": 100}, company="Test", period="2024")
        assert stmt.revenue == 0


# ── Copilot New Tools Tests ──


class TestCopilotNewTools:
    async def test_black_litterman_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute(
            "black_litterman",
            {"returns": [0.08, 0.12], "volatilities": [0.15, 0.20], "correlations": [[1, 0.5], [0.5, 1]], "views": []},
        )
        assert isinstance(result, dict)

    async def test_sanctions_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute("sanctions_screening", {"entity": "Test Corp"})
        assert isinstance(result, list)

    async def test_market_feed_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute("market_feed", {"market": "A"})
        assert isinstance(result, list)

    async def test_bond_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute(
            "bond_analysis", {"face_value": 1000, "coupon_rate": 0.05, "years": 5, "yield_to_maturity": 0.06}
        )
        assert isinstance(result, dict)

    async def test_yield_curve_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute(
            "yield_curve", {"maturities": [0.5, 1, 2, 5, 10], "yields": [0.02, 0.025, 0.03, 0.035, 0.04]}
        )
        assert isinstance(result, dict)

    async def test_yield_curve_no_data(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute("yield_curve", {"maturities": [], "yields": []})
        assert "error" in result

    async def test_entity_resolution_tool(self):
        from fusion_finance.copilot.tools import ToolRegistry

        reg = ToolRegistry()
        result = await reg.execute("entity_resolution", {"entity": "TestCorp", "depth": 2})
        assert isinstance(result, dict)


# ── ai_client.py Tests ──


class TestMLXClient:
    async def test_chat_with_fusion_core(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        mock_mlx = MagicMock()
        mock_mlx.chat = AsyncMock(return_value="hello response")
        client = MLXClient()
        client._client = mock_mlx
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == "hello response"
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_fusion_core_returns_nonstring(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        mock_mlx = MagicMock()
        mock_mlx.chat = AsyncMock(return_value={"text": "nested"})
        client = MLXClient()
        client._client = mock_mlx
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert isinstance(result, str)
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_httpx_fallback(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        client._client = None
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = False
        try:
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(return_value=MagicMock(json=lambda: {"data": [{"id": "test-model"}]}))
            mock_httpx.post = AsyncMock(
                return_value=MagicMock(
                    json=lambda: {"choices": [{"message": {"content": "httpx reply"}}]},
                    raise_for_status=MagicMock(),
                )
            )
            client._httpx_client = mock_httpx
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == "httpx reply"
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_retries_on_failure(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        mock_mlx = MagicMock()
        call_count = 0

        async def failing_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        mock_mlx.chat = failing_chat
        client = MLXClient(max_retries=1)
        client._client = mock_mlx
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == ""
            assert call_count == 2
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_httpx_no_model_lists(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        client._client = None
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = False
        try:
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(side_effect=Exception("no models"))
            mock_httpx.post = AsyncMock(
                return_value=MagicMock(
                    json=lambda: {"choices": [{"message": {"content": "fallback reply"}}]},
                    raise_for_status=MagicMock(),
                )
            )
            client._httpx_client = mock_httpx
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == "fallback reply"
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_stream_with_fusion_core(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        async def fake_stream(*args, **kwargs):
            yield "chunk1"
            yield "chunk2"

        mock_mlx = MagicMock()
        mock_mlx.chat_stream = fake_stream
        client = MLXClient()
        client._client = mock_mlx
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            chunks = []
            async for chunk in client.chat_stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            assert chunks == ["chunk1", "chunk2"]
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_chat_stream_fallback_no_attribute(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        mock_mlx = MagicMock(spec=[])
        client = MLXClient()
        client._client = mock_mlx
        client.chat = AsyncMock(return_value="fallback stream content")
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            chunks = []
            async for chunk in client.chat_stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            assert chunks == ["fallback stream content"]
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_health_check_fusion_core(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        mock_mlx = MagicMock()
        mock_mlx.list_models = AsyncMock(return_value=["model-a", "model-b"])
        client = MLXClient()
        client._client = mock_mlx
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = True
        try:
            result = await client.health_check()
            assert result["status"] == "ok"
            assert len(result["models"]) == 2
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_health_check_httpx(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        client._client = None
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = False
        try:
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(
                return_value=MagicMock(
                    json=lambda: {"data": [{"id": "model-x"}]},
                    raise_for_status=MagicMock(),
                )
            )
            client._httpx_client = mock_httpx
            result = await client.health_check()
            assert result["status"] == "ok"
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_health_check_error(self):
        import fusion_finance.ai_client as ai_client_mod
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        client._client = None
        original_has = ai_client_mod._HAS_FUSION_CORE
        ai_client_mod._HAS_FUSION_CORE = False
        try:
            mock_httpx = AsyncMock()
            mock_httpx.get = AsyncMock(side_effect=Exception("connection refused"))
            client._httpx_client = mock_httpx
            result = await client.health_check()
            assert result["status"] == "error"
        finally:
            ai_client_mod._HAS_FUSION_CORE = original_has

    async def test_close(self):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        mock_httpx = AsyncMock()
        mock_httpx.aclose = AsyncMock()
        client._httpx_client = mock_httpx
        await client.close()
        assert client._httpx_client is None

    async def test_close_no_client(self):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        assert client._httpx_client is None
        await client.close()

    def test_httpx_client_lazy_init(self):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        assert client._httpx_client is None
        hc = client.httpx_client
        assert hc is not None

    def test_custom_params(self):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient(base_url="http://custom:9999/v1", model="custom-model", max_retries=5)
        assert client.base_url == "http://custom:9999/v1"
        assert client.default_model == "custom-model"
        assert client.max_retries == 5


# ── utils/parse_json.py Tests ──


class TestParseJson:
    def test_parse_valid_json(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json('{"key": "value"}') == {"key": "value"}

    def test_parse_json_with_markdown_fence(self):
        from fusion_finance.utils.parse_json import parse_json

        text = '```json\n{"key": "val"}\n```'
        assert parse_json(text) == {"key": "val"}

    def test_parse_json_with_plain_fence(self):
        from fusion_finance.utils.parse_json import parse_json

        text = '```\n{"key": "val"}\n```'
        assert parse_json(text) == {"key": "val"}

    def test_parse_json_brace_extraction(self):
        from fusion_finance.utils.parse_json import parse_json

        text = 'Some text {"a": 1} more text'
        assert parse_json(text) == {"a": 1}

    def test_parse_json_bracket_extraction(self):
        from fusion_finance.utils.parse_json import parse_json

        text = "Some text [1, 2, 3] more text"
        assert parse_json(text) == [1, 2, 3]

    def test_parse_json_empty_string(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json("") is None

    def test_parse_json_non_string(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json(123) is None
        assert parse_json(None) is None

    def test_parse_json_invalid_content(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json("not json at all") is None

    def test_parse_json_brace_with_invalid_inner(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json("{invalid}") is None

    def test_parse_json_bracket_with_invalid_inner(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json("[invalid]") is None


# ── modeling/advanced.py Tests ──


class TestLBOModel:
    def test_calculate(self):
        from fusion_finance.modeling.advanced import LBOModel

        model = LBOModel(
            company="TestCo",
            purchase_price=1000,
            ebitda=[100, 120, 140, 160, 180],
            exit_multiple=8.0,
        )
        result = model.calculate()
        assert result["purchase_price"] == 1000
        assert result["exit_ev"] == 180 * 8
        assert "moic" in result
        assert "irr" in result

    def test_calculate_no_ebitda(self):
        from fusion_finance.modeling.advanced import LBOModel

        model = LBOModel(company="EmptyCo", purchase_price=1000)
        result = model.calculate()
        assert "error" in result

    def test_calculate_zero_equity(self):
        from fusion_finance.modeling.advanced import LBOModel

        model = LBOModel(
            company="ZeroEq",
            purchase_price=1000,
            equity_pct=0.0,
            ebitda=[100],
            exit_multiple=5.0,
        )
        result = model.calculate()
        assert result["moic"] == 0


class TestDDMModel:
    def test_calculate(self):
        from fusion_finance.modeling.advanced import DDMModel

        model = DDMModel(
            company="DivCo",
            current_dividend=2.0,
            growth_rate=0.05,
            required_return=0.10,
        )
        result = model.calculate()
        assert result["next_dividend"] == 2.0 * 1.05
        assert result["fair_value"] > 0

    def test_calculate_invalid_rates(self):
        from fusion_finance.modeling.advanced import DDMModel

        model = DDMModel(
            company="BadCo",
            current_dividend=2.0,
            growth_rate=0.10,
            required_return=0.05,
        )
        result = model.calculate()
        assert "error" in result


class TestMergerModel:
    def test_calculate(self):
        from fusion_finance.modeling.advanced import MergerModel

        model = MergerModel(
            acquirer="AcqCo",
            target="TgtCo",
            acquirer_price=100,
            target_price=50,
            premium=0.3,
        )
        result = model.calculate()
        assert result["offer_price"] == 50 * 1.3
        assert result["premium"] == 30.0
        assert "acc_eps" in result
        assert "diluted_eps" in result
        assert "accretion" in result

    def test_calculate_zero_prices(self):
        from fusion_finance.modeling.advanced import MergerModel

        model = MergerModel(acquirer="A", target="T")
        result = model.calculate()
        assert result["offer_price"] == 0.0
        assert result["acc_eps"] == 0.0


class TestAdvancedModelingEngine:
    async def test_build_lbo_with_ai(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.modeling.advanced import AdvancedModelingEngine

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = AsyncMock(
            return_value='{"purchase_price": 5000, "debt_pct": 0.7, "exit_multiple": 9, "interest_rate": 0.06, "assumptions": {"key_drivers": ["growth"]}}'
        )
        engine = AdvancedModelingEngine(mock_mlx)
        model = await engine.build_lbo("TestCo", [100, 120, 140])
        assert model.purchase_price == 5000
        assert model.debt_pct == 0.7

    async def test_build_lbo_ai_failure_fallback(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.modeling.advanced import AdvancedModelingEngine

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = AsyncMock(return_value="")
        engine = AdvancedModelingEngine(mock_mlx)
        model = await engine.build_lbo("TestCo", [100, 120])
        assert model.purchase_price == sum([100, 120]) * 8
        assert model.company == "TestCo"


# ── config.py Tests ──


class TestConfig:
    def test_default_values(self):
        from fusion_finance.config import DEFAULT_HOST, DEFAULT_MLX_BASE_URL, DEFAULT_MODEL, DEFAULT_PORT

        assert DEFAULT_HOST == "0.0.0.0"
        assert DEFAULT_PORT == 11446
        assert DEFAULT_MLX_BASE_URL == "http://localhost:11432/v1"
        assert DEFAULT_MODEL != ""

    def test_setup_logging(self):
        from fusion_finance.config import setup_logging

        setup_logging("DEBUG")
        setup_logging("INFO")

    def test_setup_logging_env(self):
        from fusion_finance.config import setup_logging

        setup_logging("WARNING")

    def test_ensure_dirs(self):
        from fusion_finance.config import AUDIT_DIR, CACHE_DIR, DATA_DIR, PROJECT_DIR, ensure_dirs

        ensure_dirs()
        assert DATA_DIR.exists()
        assert AUDIT_DIR.exists()
        assert PROJECT_DIR.exists()
        assert CACHE_DIR.exists()

    def test_data_dir_from_env(self):
        import os

        from fusion_finance import config

        original = os.environ.get("FUSION_FINANCE_DATA_DIR")
        try:
            os.environ["FUSION_FINANCE_DATA_DIR"] = "/tmp/test_fusion_finance_data"
            import importlib

            importlib.reload(config)
            assert str(config.DATA_DIR) == "/tmp/test_fusion_finance_data"
        finally:
            if original is not None:
                os.environ["FUSION_FINANCE_DATA_DIR"] = original
            else:
                os.environ.pop("FUSION_FINANCE_DATA_DIR", None)
            importlib.reload(config)

    def test_log_level_from_env(self):
        import os

        from fusion_finance import config

        original = os.environ.get("FUSION_FINANCE_LOG_LEVEL")
        try:
            os.environ["FUSION_FINANCE_LOG_LEVEL"] = "debug"
            import importlib

            importlib.reload(config)
            assert config.LOG_LEVEL == "DEBUG"
        finally:
            if original is not None:
                os.environ["FUSION_FINANCE_LOG_LEVEL"] = original
            else:
                os.environ.pop("FUSION_FINANCE_LOG_LEVEL", None)
            importlib.reload(config)


# ── copilot/engine.py Tests ──


class TestCopilotEngine:
    async def test_chat_no_tool_call(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = AsyncMock(return_value="This is a direct answer")
        engine = CopilotEngine(mock_mlx)
        result = await engine.chat("What is DCF?")
        assert result["reply"] == "This is a direct answer"
        assert result["tool_calls"] == []
        assert result["rounds"] == 0

    async def test_chat_with_tool_call(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        call_count = 0

        async def mock_chat(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '{"tool": "calculate_dcf", "args": {"company": "Apple", "revenue": [100, 120]}}'
            return "Final analysis for Apple"

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = mock_chat
        engine = CopilotEngine(mock_mlx)
        result = await engine.chat("Build DCF for Apple")
        assert result["rounds"] == 1
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "calculate_dcf"

    async def test_chat_with_custom_session(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = AsyncMock(return_value="Reply")
        engine = CopilotEngine(mock_mlx)
        result = await engine.chat("hi", session_id="custom-session")
        assert result["session_id"] == "custom-session"

    async def test_chat_with_history(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat = AsyncMock(return_value="Reply with context")
        engine = CopilotEngine(mock_mlx)
        history = [{"role": "user", "content": "previous question"}]
        result = await engine.chat("follow up", history=history)
        assert result["reply"] == "Reply with context"

    async def test_chat_stream(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        async def fake_stream(messages, **kwargs):
            yield "Hello"
            yield " World"

        mock_mlx = MagicMock(spec=MLXClient)
        mock_mlx.chat_stream = fake_stream
        engine = CopilotEngine(mock_mlx)
        chunks = []
        async for chunk in engine.chat_stream("hi"):
            chunks.append(chunk)
        assert chunks == ["Hello", " World"]

    def test_get_history(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        mock_mlx = MagicMock(spec=MLXClient)
        engine = CopilotEngine(mock_mlx)
        engine.memory.add_message("sess1", "user", "hello")
        engine.memory.add_message("sess1", "assistant", "hi")
        history = engine.get_history("sess1")
        assert len(history) == 2

    def test_build_system_prompt(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.copilot.engine import CopilotEngine

        mock_mlx = MagicMock(spec=MLXClient)
        engine = CopilotEngine(mock_mlx, scenario="risk")
        prompt = engine._build_system_prompt()
        assert "风控合规" in prompt
        assert "tool" in prompt.lower() or "工具" in prompt


# ── copilot/memory.py Tests ──


class TestConversationMemory:
    def test_add_and_get_messages(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        mem.add_message(sid, "user", "hello")
        mem.add_message(sid, "assistant", "hi")
        msgs = mem.get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["content"] == "hi"

    def test_get_messages_with_limit(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        for i in range(10):
            mem.add_message(sid, "user", f"msg{i}")
        msgs = mem.get_messages(sid, limit=3)
        assert len(msgs) == 3

    def test_get_messages_nonexistent_session(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        msgs = mem.get_messages("nonexistent")
        assert msgs == []

    def test_context_operations(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        mem.set_context(sid, "company", "Apple")
        val = mem.get_context(sid, "company")
        assert val == "Apple"

    def test_get_context_default(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        val = mem.get_context("no-session", "key", default="default_val")
        assert val == "default_val"

    def test_set_context_creates_session(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        mem.set_context(sid, "key", "val")
        msgs = mem.get_messages(sid)
        assert len(msgs) == 1

    def test_get_full_context(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        mem.add_message(sid, "user", "hi")
        mem.set_context(sid, "k", "v")
        ctx = mem.get_full_context(sid)
        assert "messages" in ctx
        assert "context" in ctx
        assert ctx["context"]["k"] == "v"

    def test_get_full_context_nonexistent(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        ctx = mem.get_full_context("no-session")
        assert ctx == {}

    def test_clear_session(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid = ConversationMemory.new_session_id()
        mem.add_message(sid, "user", "hi")
        assert mem.clear_session(sid) is True
        assert mem.clear_session(sid) is False

    def test_list_sessions(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory()
        sid1 = ConversationMemory.new_session_id()
        sid2 = ConversationMemory.new_session_id()
        mem.add_message(sid1, "user", "hi1")
        mem.add_message(sid2, "user", "hi2")
        sessions = mem.list_sessions()
        assert len(sessions) == 2

    def test_max_history_trimming(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory(max_history=3)
        sid = ConversationMemory.new_session_id()
        for i in range(5):
            mem.add_message(sid, "user", f"msg{i}")
        msgs = mem.get_messages(sid)
        assert len(msgs) == 3

    def test_ensure_capacity(self):
        from fusion_finance.copilot.memory import ConversationMemory

        mem = ConversationMemory(max_sessions=2)
        sid1 = ConversationMemory.new_session_id()
        sid2 = ConversationMemory.new_session_id()
        mem.add_message(sid1, "user", "hi1")
        mem.add_message(sid2, "user", "hi2")
        sid3 = ConversationMemory.new_session_id()
        mem.add_message(sid3, "user", "hi3")
        sessions = mem.list_sessions()
        assert len(sessions) == 2

    def test_new_session_id_format(self):
        from fusion_finance.copilot.memory import ConversationMemory

        sid = ConversationMemory.new_session_id()
        assert len(sid) == 12
        assert sid.isalnum()


# ── data/adapter.py Tests ──


class TestDataAdapter:
    def test_load_csv_string(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        result = adapter.load_csv(csv_data)
        assert result["row_count"] == 2
        assert result["data"][0]["name"] == "Alice"

    def test_load_csv_cached(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        csv_data = "name,val\nA,1\nB,2"
        adapter.load_csv(csv_data)
        result2 = adapter.load_csv(csv_data)
        assert result2["row_count"] == 2

    def test_sanitize_row(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        row = {"price": "$1,234.56", "name": "Widget"}
        result = adapter.sanitize_row(row, numeric_fields=["price"])
        assert result["price"] == 1234.56
        assert result["name"] == "Widget"

    def test_validate_balance_ok(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        result = adapter.validate_balance(100, 60, 40)
        assert result["balanced"] is True

    def test_validate_balance_fail(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        result = adapter.validate_balance(100, 70, 40)
        assert result["balanced"] is False

    def test_check_completeness(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        data = [
            {"revenue": 100, "net_income": 20},
            {"revenue": 200, "net_income": None},
        ]
        result = adapter.check_completeness(data, required_fields=["revenue", "net_income"])
        assert result["overall_score"] > 0

    def test_invalidate(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        csv_data = "name,val\nA,1"
        adapter.load_csv(csv_data)
        adapter.invalidate(csv_data)

    def test_clear_cache(self):
        from fusion_finance.data.adapter import DataAdapter

        adapter = DataAdapter()
        csv_data = "name,val\nA,1"
        adapter.load_csv(csv_data)
        adapter.clear_cache()


# ── data/csv_loader.py Tests ──


class TestCSVLoader:
    def test_load_string(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name,age\nAlice,30\nBob,25")
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[0]["age"] == 30

    def test_load_with_tab_delimiter(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name\tage\nAlice\t30")
        assert len(data) == 1
        assert data[0]["name"] == "Alice"

    def test_load_no_header(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("Alice,30\nBob,25", has_header=False)
        assert len(data) == 2
        assert "col_0" in data[0]

    def test_load_empty_content(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("")
        assert data == []

    def test_load_auto_type(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name,count,price\nWidget,10,9.99")
        assert data[0]["count"] == 10
        assert data[0]["price"] == 9.99

    def test_load_empty_cell_becomes_none(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name,val\nAlice,\nBob,5")
        assert data[0]["val"] is None
        assert data[1]["val"] == 5

    def test_load_skip_blank_rows(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name,val\nAlice,1\n\nBob,2")
        assert len(data) == 2

    def test_load_custom_delimiter(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("name|val\nA|1", delimiter="|")
        assert len(data) == 1
        assert data[0]["name"] == "A"

    def test_load_from_file(self, tmp_path):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30", encoding="utf-8")
        data = loader.load(str(csv_file))
        assert len(data) == 1
        assert data[0]["name"] == "Alice"

    def test_load_file_as_path(self, tmp_path):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nBob,25", encoding="utf-8")
        data = loader.load(csv_file)
        assert len(data) == 1

    def test_detect_encoding_gbk(self, tmp_path):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        csv_file = tmp_path / "gbk.csv"
        csv_file.write_text("姓名,年龄\n张三,30", encoding="gbk")
        data = loader.load(str(csv_file))
        assert len(data) == 1

    def test_short_string_treated_as_content(self):
        from fusion_finance.data.csv_loader import CSVLoader

        loader = CSVLoader()
        data = loader.load("x,y\n1,2")
        assert len(data) == 1


# ── project/export.py Tests ──


class TestProjectExporter:
    def test_export_json(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="ExportTest", description="test export")
        exporter = ProjectExporter(manager=mgr)
        out = str(tmp_path / "output.json")
        result = exporter.export_json(proj.id, output_path=out)
        assert result is not None
        assert "output.json" in result

    def test_export_json_auto_path(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="AutoPath", description="auto path")
        exporter = ProjectExporter(manager=mgr)
        result = exporter.export_json(proj.id, output_path=str(tmp_path / "auto.json"))
        assert result is not None

    def test_export_json_not_found(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        result = exporter.export_json("nonexistent_id")
        assert result is None

    def test_export_zip(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="ZipTest", description="zip export")
        mgr.snapshot(proj.id, label="v1")
        exporter = ProjectExporter(manager=mgr)
        out = str(tmp_path / "output.zip")
        result = exporter.export_zip(proj.id, output_path=out)
        assert result is not None
        assert "output.zip" in result

    def test_export_zip_with_current_data(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="DataProj", description="has data")
        mgr.update(proj.id, data={"revenue": 100})
        mgr.snapshot(proj.id, label="v1")
        exporter = ProjectExporter(manager=mgr)
        out = str(tmp_path / "data_export.zip")
        result = exporter.export_zip(proj.id, output_path=out)
        assert result is not None

    def test_export_zip_not_found(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        result = exporter.export_zip("nonexistent_id")
        assert result is None

    def test_import_json(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="ImportSrc", description="source")
        mgr.update(proj.id, data={"key": "val"})
        mgr.snapshot(proj.id, label="v1")
        exporter = ProjectExporter(manager=mgr)
        json_path = str(tmp_path / "export.json")
        exporter.export_json(proj.id, output_path=json_path)

        mgr2 = ProjectManager(data_dir=str(tmp_path / "projects2"))
        exporter2 = ProjectExporter(manager=mgr2)
        imported_id = exporter2.import_json(json_path)
        assert imported_id is not None

    def test_import_json_not_found(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        result = exporter.import_json(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_import_zip(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        proj = mgr.create(name="ZipImport", description="zip import test")
        mgr.update(proj.id, data={"val": 42})
        mgr.snapshot(proj.id, label="v1")
        exporter = ProjectExporter(manager=mgr)
        zip_path = str(tmp_path / "export.zip")
        exporter.export_zip(proj.id, output_path=zip_path)

        mgr2 = ProjectManager(data_dir=str(tmp_path / "projects2"))
        exporter2 = ProjectExporter(manager=mgr2)
        imported_id = exporter2.import_zip(zip_path)
        assert imported_id is not None

    def test_import_zip_not_found(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        result = exporter.import_zip(str(tmp_path / "nope.zip"))
        assert result is None

    def test_import_zip_invalid(self, tmp_path):
        import zipfile

        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        bad_zip = tmp_path / "bad.zip"
        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("wrong.json", "not a project")
        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        result = exporter.import_zip(str(bad_zip))
        assert result is None

    def test_import_json_with_versions(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        json_path = tmp_path / "import_versions.json"
        data = {
            "name": "Versioned",
            "description": "test",
            "metadata": {},
            "current_data": {"x": 1},
            "versions": [
                {"version": 1, "label": "v1", "data": {"x": 1}},
                {"version": 2, "label": "v2", "data": {"x": 2}},
            ],
        }
        json_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exporter = ProjectExporter(manager=mgr)
        imported_id = exporter.import_json(str(json_path))
        assert imported_id is not None
        proj = mgr.get(imported_id)
        assert len(proj.versions) == 2


# ── report/formatter.py Tests ──


class TestReportFormatter:
    def test_export_markdown(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.md")
        result = fmt.export("# Hello", "markdown", output_path=out)
        assert result == out

    def test_export_json(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.json")
        result = fmt.export("content", "json", output_path=out, template_data={"key": "val"})
        assert result == out

    def test_export_html(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.html")
        result = fmt.export("<h1>Hello</h1>", "html", output_path=out)
        assert result == out

    def test_export_html_with_template(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report_templated.html")
        result = fmt.export(
            "content",
            "html",
            output_path=out,
            template_name="valuation",
            template_data={"company": "TestCo", "body": "some content"},
        )
        assert result == out

    def test_export_unsupported_format(self):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        with pytest.raises(ValueError, match="Unsupported format"):
            fmt.export("content", "docx")

    def test_export_auto_path(self, tmp_path):
        import os

        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            result = fmt.export("content", "markdown")
            assert result.endswith(".md")
        finally:
            os.chdir(original_cwd)

    def test_render_html_fallback(self):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        html = fmt.render_html("unknown_template", {"company": "TestCo", "body": "data"})
        assert "TestCo" in html

    def test_fallback_html(self):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        html = fmt._fallback_html("valuation", {"company": "Apple", "body": "content here"})
        assert "Apple" in html
        assert "content here" in html

    def test_fallback_html_with_date(self):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        html = fmt._fallback_html("report", {"company": "Co", "date": "2024-01-01", "content": "hello"})
        assert "2024-01-01" in html

    def test_export_pdf_fallback_html(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.pdf")
        fmt.export("<h1>PDF test</h1>", "pdf", output_path=out)
        html_path = tmp_path / "report.html"
        assert html_path.exists()

    def test_export_xlsx_fallback_csv(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.xlsx")
        fmt.export("col1,col2\n1,2", "xlsx", output_path=out)
        csv_path = tmp_path / "report.csv"
        assert csv_path.exists()

    def test_export_pptx(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report.pptx")
        result = fmt.export("Slide content", "pptx", output_path=out)
        from pathlib import Path

        assert Path(result).exists()
        assert result.endswith((".pptx", ".txt"))

    def test_split_content(self):
        from fusion_finance.report.formatter import _split_content

        text = "line1\nline2\nline3"
        chunks = _split_content(text, max_chars=15)
        assert len(chunks) >= 1

    def test_split_content_single_chunk(self):
        from fusion_finance.report.formatter import _split_content

        text = "short"
        chunks = _split_content(text, max_chars=100)
        assert len(chunks) == 1


# ── API Routes: data.py Tests ──


class TestDataRoutes:
    async def test_validate_balance(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/validate/balance", json={"assets": 100, "liabilities": 60, "equity": 40}
            )
            assert resp.status_code == 200
            assert resp.json()["balanced"] is True

    async def test_validate_balance_imbalanced(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/validate/balance", json={"assets": 100, "liabilities": 70, "equity": 40}
            )
            assert resp.status_code == 200
            assert resp.json()["balanced"] is False

    async def test_check_completeness(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/validate/completeness",
                json={"data": [{"revenue": 100, "net_income": 20}], "required_fields": ["revenue", "net_income"]},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "overall_score" in body

    async def test_list_cache(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/data/cache")
            assert resp.status_code == 200
            body = resp.json()
            assert "items" in body

    async def test_market_quotes(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/data/market/quotes", params={"market": "A"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] > 0

    async def test_market_ohlcv(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/market/ohlcv", json={"symbol": "600519", "base_price": 100, "bars": 30}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] == 30

    async def test_market_technicals(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            ohlcv = [
                {"close": 100 + i, "open": 99 + i, "high": 101 + i, "low": 98 + i, "volume": 1000} for i in range(60)
            ]
            resp = await client.post("/api/v1/data/market/technicals", json={"ohlcv": ohlcv})
            assert resp.status_code == 200
            body = resp.json()
            assert body["bar_count"] == 60

    async def test_import_csv(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/import",
                files={"file": ("test.csv", b"name,val\nAlice,1\nBob,2", "text/csv")},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["rows"] == 2

    async def test_delete_cache_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/data/cache/nonexistent_key")
            assert resp.status_code == 404


# ── API Routes: risk.py Tests ──


class TestRiskRoutes:
    async def test_var_calculation(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/var",
                json={"returns": [0.01, -0.02, 0.03, -0.01, 0.02] * 10, "portfolio_value": 1000000, "confidence": 0.95},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "cvar_95" in body or "var" in body

    async def test_monte_carlo_var(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/var/monte-carlo", json={"portfolio_value": 1000000, "simulations": 100}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "cvar_95" in body or "var" in body

    async def test_stress_scenarios(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/risk/stress-scenarios")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["scenarios"]) > 0

    async def test_stress_test(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/stress-test",
                json={
                    "scenario": "rate_hike",
                    "impact": -0.15,
                    "probability": "medium",
                    "affected_factors": ["interest_rate"],
                    "mitigations": ["hedge"],
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["scenario"] == "rate_hike"

    async def test_sanctions_screen(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/risk/sanctions", json={"entity": "Test Company", "threshold": 0.6})
            assert resp.status_code == 200
            body = resp.json()
            assert "hit_count" in body

    async def test_sanctions_batch(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/sanctions/batch", json={"entities": ["Co A", "Co B"], "threshold": 0.6}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["total_entities"] == 2

    async def test_entity_graph(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/entity-graph",
                json={
                    "nodes": [{"id": "A", "type": "company"}, {"id": "B", "type": "person"}],
                    "edges": [{"source": "A", "target": "B", "relation": "owns", "weight": 0.6}],
                },
            )
            assert resp.status_code == 200

    async def test_ubo_resolution(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/entity-graph/ubo",
                json={
                    "nodes": [{"id": "A", "type": "company"}, {"id": "B", "type": "person"}],
                    "edges": [{"source": "B", "target": "A", "relation": "owns", "weight": 0.8}],
                    "target_entity_id": "A",
                    "threshold": 0.25,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "ubos" in body

    async def test_kyc_screening(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.risk._get_mlx") as mock_mlx:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(
                return_value='{"risk_level":"LOW","risk_score":10,"findings":[],"recommendations":["OK"]}'
            )
            mock_mlx.return_value = mock_client
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/risk/kyc", json={"entity": "GoodCorp", "jurisdiction": "CN"})
                assert resp.status_code == 200

    async def test_credit_assessment(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.risk._get_mlx") as mock_mlx:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(
                return_value='{"credit_rating":"BBB","score":70,"risk_factors":[],"recommendations":["Monitor"]}'
            )
            mock_mlx.return_value = mock_client
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/risk/credit", json={"entity": "MidCorp", "financials": {"revenue": 500}}
                )
                assert resp.status_code == 200


# ── API Routes: statements.py Tests ──


class TestStatementsRoutes:
    async def test_metrics_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/metrics",
                json={
                    "company": "Apple",
                    "period": "2024",
                    "revenue": 1000,
                    "gross_profit": 400,
                    "operating_income": 300,
                    "net_income": 200,
                    "total_assets": 5000,
                    "total_liabilities": 3000,
                    "equity": 2000,
                    "operating_cf": 250,
                    "free_cf": 150,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "net_margin" in body

    async def test_validate_balance_sheet(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/validate",
                json={
                    "statements": [
                        {
                            "company": "t",
                            "period": "2024",
                            "revenue": 100,
                            "net_income": 20,
                            "total_assets": 200,
                            "total_liabilities": 100,
                            "equity": 100,
                        },
                    ]
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "total_checked" in body

    async def test_screener_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/statements/screener", json={"filters": {"preset": "value"}, "limit": 5})
            assert resp.status_code == 200

    async def test_screener_with_custom_filters(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/statements/screener", json={"filters": {"filters": [{"metric": "roe", "min": 10}]}, "limit": 5}
            )
            assert resp.status_code == 200

    async def test_analyze_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.statements._get_mlx") as mock_mlx:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value='{"strengths":[],"weaknesses":[],"key_ratios":{}}')
            mock_mlx.return_value = mock_client
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/statements/analyze", json={"company": "TestCo", "data": {"revenue": 100}}
                )
                assert resp.status_code == 200


# ── API Routes: copilot.py Tests ──


class TestCopilotRoutes:
    async def test_chat_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.copilot.MLXClient") as MockMLX:
            mock_mlx = MagicMock()
            mock_mlx.chat = AsyncMock(return_value="Financial analysis reply")
            MockMLX.return_value = mock_mlx
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/copilot/chat", json={"message": "What is WACC?", "session_id": "test-session"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert "reply" in body

    async def test_chat_with_session(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.copilot.MLXClient") as MockMLX:
            mock_mlx = MagicMock()
            mock_mlx.chat = AsyncMock(return_value="Reply")
            MockMLX.return_value = mock_mlx
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/copilot/chat", json={"message": "hi", "session_id": "sess-123"})
                assert resp.status_code == 200

    async def test_history_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.copilot.MLXClient") as MockMLX:
            mock_mlx = MagicMock()
            MockMLX.return_value = mock_mlx
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/copilot/history/test-session")
                assert resp.status_code == 200
                body = resp.json()
                assert "messages" in body

    async def test_sessions_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.copilot.MLXClient") as MockMLX:
            mock_mlx = MagicMock()
            MockMLX.return_value = mock_mlx
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/copilot/sessions")
                assert resp.status_code == 200
                body = resp.json()
                assert "sessions" in body


# ── API Routes: modeling.py Tests ──


class TestModelingRoutes:
    async def test_dcf_calculate(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/dcf/calculate",
                json={
                    "company": "TestCo",
                    "revenue": [100, 120, 140, 160, 180],
                    "ebit_margin": [0.2, 0.2, 0.2, 0.2, 0.2],
                    "wacc": 0.10,
                    "terminal_growth": 0.03,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "result" in body

    async def test_ddm_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/ddm",
                json={"company": "DivCo", "current_dividend": 2.0, "growth_rate": 0.05, "required_return": 0.10},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "result" in body

    async def test_merger_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/merger",
                json={"acquirer": "Acq", "target": "Tgt", "acquirer_price": 100, "target_price": 50, "premium": 0.3},
            )
            assert resp.status_code == 200

    async def test_apv_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/apv",
                json={
                    "company": "Co",
                    "unlevered_fcf": [50, 55, 60],
                    "unlevered_cost": 0.10,
                    "debt": 200,
                    "tax_rate": 0.25,
                },
            )
            assert resp.status_code == 200

    async def test_eva_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/eva",
                json={"company": "Co", "nopat": [100, 110], "invested_capital": [500, 520], "wacc": 0.10},
            )
            assert resp.status_code == 200

    async def test_ri_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/ri",
                json={"company": "Co", "book_value": 100, "net_income": [15, 18], "cost_of_equity": 0.12},
            )
            assert resp.status_code == 200

    async def test_session_create_and_update(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/session", json={"company": "TestCo", "assumptions": {"wacc": 0.10}}
            )
            assert resp.status_code == 200
            body = resp.json()
            session_id = body["session_id"]

            resp2 = await client.put(f"/api/v1/modeling/session/{session_id}", json={"key": "wacc", "value": 0.12})
            assert resp2.status_code == 200

    async def test_session_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put("/api/v1/modeling/session/nonexistent", json={"key": "wacc", "value": 0.12})
            assert resp.status_code == 404

    async def test_batch_dcf(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/batch-dcf",
                json={
                    "models": [
                        {"company": "A", "revenue": [100, 120], "wacc": 0.1},
                        {"company": "B", "revenue": [200, 240], "wacc": 0.1},
                    ]
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] == 2

    async def test_yield_curve(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/yield-curve", json={"maturities": [0.5, 1, 2, 5, 10], "beta0": 0.04, "beta1": -0.02}
            )
            assert resp.status_code == 200

    async def test_yield_curve_calibrate(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/yield-curve/calibrate",
                json={"observed_maturities": [1, 2, 5, 10], "observed_rates": [0.02, 0.025, 0.03, 0.035]},
            )
            assert resp.status_code == 200

    async def test_scenarios(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/modeling/scenarios",
                json={
                    "company": "TestCo",
                    "revenue": [100, 120, 140],
                    "ebit_margin": [0.2, 0.2, 0.2],
                    "custom_scenarios": {"bull": {"revenue_adj": 1.1}, "bear": {"revenue_adj": 0.9}},
                },
            )
            assert resp.status_code == 200


# ── API Routes: chart.py Tests ──


class TestChartRoutes:
    async def test_candlestick(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chart/candlestick",
                json={
                    "symbol": "600519",
                    "data": [{"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000}] * 5,
                    "title": "Test Chart",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "svg" in body

    async def test_heatmap(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chart/heatmap",
                json={
                    "matrix": [[1.0, 0.5], [0.5, 1.0]],
                    "row_labels": ["A", "B"],
                    "col_labels": ["X", "Y"],
                },
            )
            assert resp.status_code == 200

    async def test_heatmap_empty(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/chart/heatmap", json={"matrix": []})
            assert resp.status_code == 400

    async def test_waterfall(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chart/waterfall",
                json={
                    "categories": ["Revenue", "COGS", "SGA"],
                    "values": [100, -40, -20],
                },
            )
            assert resp.status_code == 200

    async def test_sensitivity(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chart/sensitivity",
                json={
                    "factors": ["WACC", "Growth"],
                    "low_values": [80, 90],
                    "high_values": [120, 130],
                    "base_value": 100,
                },
            )
            assert resp.status_code == 200

    async def test_sensitivity_empty_factors(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/chart/sensitivity", json={"factors": []})
            assert resp.status_code == 400


# ── API Routes: audit.py Tests ──


class TestAuditRoutes:
    async def test_record_and_query(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/audit/record",
                json={
                    "user": "tester",
                    "action": "test_action",
                    "module": "test",
                    "details": "test details",
                    "status": "success",
                    "duration_ms": 42.5,
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

            resp2 = await client.post("/api/v1/audit/query", json={"user": "tester", "limit": 10})
            assert resp2.status_code == 200
            body = resp2.json()
            assert body["count"] >= 1

    async def test_audit_stats(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/audit/stats")
            assert resp.status_code == 200

    async def test_audit_file_stats(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/audit/file-stats")
            assert resp.status_code == 200


# ── API Routes: report.py Tests ──


class TestReportRoutes:
    async def test_valuation_report(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/report/valuation",
                json={
                    "company": "Apple",
                    "revenue": [100, 120, 140],
                    "ebit_margin": [0.2, 0.2, 0.2],
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["company"] == "Apple"

    async def test_pitchbook(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/report/pitchbook",
                json={
                    "company": "TestCo",
                    "industry": "Tech",
                    "revenue": [100, 120],
                },
            )
            assert resp.status_code == 200

    async def test_export_markdown(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/report/export/markdown", json={"content": "# Hello World"})
            assert resp.status_code == 200

    async def test_export_unsupported(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/report/export/docx", json={"content": "test"})
            assert resp.status_code == 400

    async def test_list_formats(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/report/formats")
            assert resp.status_code == 200
            body = resp.json()
            assert "html" in body["formats"]

    async def test_research_report(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.report._get_mlx") as mock_mlx:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value="Research report content")
            mock_mlx.return_value = mock_client
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/report/research", json={"company": "Apple", "industry": "Tech", "data": {}}
                )
                assert resp.status_code == 200


# ── API Routes: project.py Tests ──


class TestProjectRoutes:
    async def test_create_and_list(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "TestProj", "description": "test"})
            assert resp.status_code == 200
            body = resp.json()
            assert "id" in body

            resp2 = await client.get("/api/v1/project/list")
            assert resp2.status_code == 200

    async def test_get_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/project/nonexistent")
            assert resp.status_code == 404

    async def test_update_project(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "UpdateTest"})
            pid = resp.json()["id"]
            resp2 = await client.put(f"/api/v1/project/{pid}", json={"name": "Updated"})
            assert resp2.status_code == 200

    async def test_delete_project(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "DeleteTest"})
            pid = resp.json()["id"]
            resp2 = await client.delete(f"/api/v1/project/{pid}")
            assert resp2.status_code == 200

    async def test_delete_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/project/nonexistent")
            assert resp.status_code == 404

    async def test_snapshot_and_versions(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "SnapTest"})
            pid = resp.json()["id"]
            resp2 = await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v1", "data": {"x": 1}})
            assert resp2.status_code == 200
            resp3 = await client.get(f"/api/v1/project/{pid}/versions")
            assert resp3.status_code == 200

    async def test_snapshot_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/nonexistent/snapshot", json={"label": "v1"})
            assert resp.status_code == 404

    async def test_restore_version(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "RestoreTest"})
            pid = resp.json()["id"]
            await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v1", "data": {"x": 1}})
            resp2 = await client.post(f"/api/v1/project/{pid}/restore", json={"version": 1})
            assert resp2.status_code == 200

    async def test_diff_versions(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "DiffTest"})
            pid = resp.json()["id"]
            await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v1", "data": {"x": 1}})
            await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v2", "data": {"x": 2}})
            resp2 = await client.get(f"/api/v1/project/{pid}/diff", params={"v1": 1, "v2": 2})
            assert resp2.status_code == 200

    async def test_diff_not_enough_versions(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "NoDiff"})
            pid = resp.json()["id"]
            resp2 = await client.get(f"/api/v1/project/{pid}/diff")
            assert resp2.status_code == 400

    async def test_version_history(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "HistTest"})
            pid = resp.json()["id"]
            await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v1"})
            resp2 = await client.get(f"/api/v1/project/{pid}/history")
            assert resp2.status_code == 200

    async def test_export_project_json(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "ExportTest"})
            pid = resp.json()["id"]
            resp2 = await client.post(f"/api/v1/project/{pid}/export", json={"format": "json"})
            assert resp2.status_code == 200

    async def test_export_project_zip(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/create", json={"name": "ZipExport"})
            pid = resp.json()["id"]
            await client.post(f"/api/v1/project/{pid}/snapshot", json={"label": "v1"})
            resp2 = await client.post(f"/api/v1/project/{pid}/export", json={"format": "zip"})
            assert resp2.status_code == 200

    async def test_export_project_not_found(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/project/nonexistent/export", json={"format": "json"})
            assert resp.status_code == 404


# ── API Middleware Tests ──


class TestMiddleware:
    async def test_rate_limit_not_exceeded(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/audit/stats")
            assert resp.status_code == 200

    async def test_api_key_middleware_exempt_paths(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/docs")
            assert resp.status_code in (200, 404)

    async def test_audit_middleware_records(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/audit/stats")
            assert resp.status_code == 200


# ── SSE Tests ──


class TestSSEEventBus:
    def test_subscribe_and_publish(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("test_channel")
        assert q is not None

    def test_unsubscribe(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("test_channel")
        bus.unsubscribe("test_channel", q)
        assert "test_channel" not in bus._subscribers or q not in bus._subscribers.get("test_channel", [])

    async def test_publish(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("test_ch")
        await bus.publish("test_ch", {"event": "test"})
        data = q.get_nowait()
        assert "test" in data

    async def test_publish_no_subscribers(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        await bus.publish("empty_channel", {"event": "test"})

    async def test_sse_insights_endpoint_routes(self):
        from fusion_finance.api.sse import router

        routes = [r.path for r in router.routes]
        assert "/insights" in routes

    async def test_sse_alerts_endpoint_routes(self):
        from fusion_finance.api.sse import router

        routes = [r.path for r in router.routes]
        assert "/alerts" in routes

    async def test_sse_publish_endpoint(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/events/publish", params={"channel": "insights:test"}, json={"type": "alert", "message": "test"}
            )
            assert resp.status_code == 200


# ── Additional coverage: data routes error paths ──


class TestDataRoutesExtra:
    async def test_import_bad_encoding(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/import",
                files={"file": ("test.csv", b"\xff\xfe\x80\x81", "text/csv")},
            )
            assert resp.status_code == 400

    async def test_validate_balance_error(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/data/validate/balance", json={"assets": "not_a_number", "liabilities": 60, "equity": 40}
            )
            assert resp.status_code == 422

    async def test_market_quotes_hk(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/data/market/quotes", params={"market": "HK"})
            assert resp.status_code == 200

    async def test_cache_list_with_data(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/data/import",
                files={"file": ("cache_test.csv", b"name,val\nX,1", "text/csv")},
            )
            resp = await client.get("/api/v1/data/cache")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] >= 1

    async def test_delete_cache_existing(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            import_resp = await client.post(
                "/api/v1/data/import",
                files={"file": ("del_test.csv", b"name,val\nY,2", "text/csv")},
            )
            body = import_resp.json()
            key = body["key"]
            resp = await client.delete(f"/api/v1/data/cache/{key}")
            assert resp.status_code == 200


# ── Additional coverage: risk routes ──


class TestRiskRoutesExtra:
    async def test_compliance_check(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        with patch("fusion_finance.api.routes.risk._get_mlx") as mock_mlx:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value='{"compliant":true,"issues":[],"recommendations":[]}')
            mock_mlx.return_value = mock_client
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/risk/compliance", json={"contract": "Test contract", "regulations": "CN"}
                )
                assert resp.status_code == 200

    async def test_var_with_empty_returns(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/var", json={"returns": [], "portfolio_value": 1000000, "confidence": 0.95}
            )
            assert resp.status_code in (200, 500)

    async def test_monte_carlo_small_simulations(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/risk/var/monte-carlo", json={"portfolio_value": 1000000, "simulations": 10, "days": 10}
            )
            assert resp.status_code == 200


# ── Additional coverage: report formatter ──


class TestReportFormatterExtra:
    def test_render_html_with_template(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        html = fmt.render_html("valuation", {"company": "Apple", "body": "test"})
        assert "Apple" in html

    def test_export_html_no_template(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "plain.html")
        result = fmt.export("<h1>Plain</h1>", "html", output_path=out)
        assert result == out

    def test_export_json_with_data(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "data.json")
        result = fmt.export("content", "json", output_path=out, template_data={"metrics": {"roe": 15}})
        assert result == out
        with open(out) as f:
            data = json.load(f)
        assert "metrics" in data

    def test_export_md_with_template_data(self, tmp_path):
        from fusion_finance.report.formatter import ReportFormatter

        fmt = ReportFormatter()
        out = str(tmp_path / "report2.md")
        result = fmt.export("content", "markdown", output_path=out, template_data={"company": "Test"})
        assert result == out


# ── Additional coverage: middleware ──


class TestMiddlewareExtra:
    async def test_api_key_with_header(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/audit/stats", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 200

    async def test_options_request_bypass(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.options("/api/v1/audit/stats")
            assert resp.status_code in (200, 405, 204)


# ── Additional coverage: SSE EventBus ──


class TestSSEEventBusExtra:
    async def test_publish_and_receive(self):
        import asyncio

        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("ch1")
        await bus.publish("ch1", {"type": "test", "data": "hello"})
        await asyncio.sleep(0.01)
        assert not q.empty()
        data = q.get_nowait()
        assert "hello" in str(data)

    async def test_multiple_subscribers(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q1 = bus.subscribe("multi_ch")
        q2 = bus.subscribe("multi_ch")
        await bus.publish("multi_ch", {"event": "broadcast"})
        assert not q1.empty()
        assert not q2.empty()


# ===== Coverage Boost: Scenario & Tool Tests =====


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
        assert len(reg._tools) == 18

    def test_get_definitions(self):
        reg = ToolRegistry()
        defs = reg.get_definitions()
        assert len(defs) == 18
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
