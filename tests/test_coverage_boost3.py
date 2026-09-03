"""Coverage-boost tests batch 3 — route except-branches + formatter/audit/normalizer unit branches."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from fusion_finance.api.app import app


@pytest.fixture(autouse=True)
def _restore_config(tmp_path):
    from fusion_finance import config

    dirs = {}
    for name in ("DATA_DIR", "AUDIT_DIR", "PROJECT_DIR", "CACHE_DIR", "EXPORT_DIR"):
        dirs[name] = getattr(config, name)
        setattr(config, name, tmp_path / name.lower())
    yield
    for name, val in dirs.items():
        setattr(config, name, val)


def _client() -> TestClient:
    return TestClient(app)


def _mock_mlx(returns="", raises=None):
    from fusion_finance.api.dependencies import get_mlx_client

    mock = MagicMock()
    if raises is not None:
        mock.chat = AsyncMock(side_effect=raises)
    else:
        mock.chat = AsyncMock(return_value=returns)
    app.dependency_overrides[get_mlx_client] = lambda: mock
    return mock


# ---------- Modeling route error branches (monkeypatch to force generic except) ----------


class TestModelingRouteErrors:
    def test_dcf_build_ai_fallback_then_generic(self, monkeypatch):
        # build_dcf always falls back to pure-math; force route generic except by breaking DCFModel.calculate
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/dcf", json={"company": "X", "revenue": [100]})
        assert resp.status_code == 422

    def test_dcf_calculate_generic(self, monkeypatch):
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/dcf/calculate", json={"company": "X", "revenue": [100]})
        assert resp.status_code == 422

    def test_dcf_calculate_model_error_branch(self, monkeypatch):
        from fusion_finance.exceptions import ModelError
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(ModelError(model_type="x")))
        c = _client()
        resp = c.post("/api/v1/modeling/dcf/calculate", json={"company": "X", "revenue": [100]})
        assert resp.status_code == 422

    def test_comps_build_generic(self, monkeypatch):
        from fusion_finance.api.routes import modeling as mod

        monkeypatch.setattr(mod, "asdict", lambda x: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/comps", json={"company": "X", "industry": "Tech"})
        assert resp.status_code == 422

    def test_sensitivity_generic(self, monkeypatch):
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/sensitivity", json={"company": "X", "revenue": [100]})
        assert resp.status_code == 422

    def test_monte_carlo_generic(self, monkeypatch):
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/monte-carlo", json={"company": "X", "revenue": [100], "simulations": 5})
        assert resp.status_code == 422

    def test_lbo_build_generic(self, monkeypatch):
        from fusion_finance.modeling import advanced as adv

        monkeypatch.setattr(adv.LBOModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/lbo", json={"company": "X", "ebitda": [100]})
        assert resp.status_code == 422

    def test_ddm_generic(self, monkeypatch):
        from fusion_finance.modeling import advanced as adv

        monkeypatch.setattr(adv.DDMModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/ddm", json={"company": "X", "current_dividend": 1})
        assert resp.status_code == 422

    def test_merger_generic(self, monkeypatch):
        from fusion_finance.modeling import advanced as adv

        monkeypatch.setattr(adv.MergerModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/merger", json={"acquirer": "A", "target": "T"})
        assert resp.status_code == 422

    def test_apv_generic(self, monkeypatch):
        from fusion_finance.modeling import valuation as val

        monkeypatch.setattr(val.APVModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/apv", json={"company": "X", "unlevered_fcf": [100]})
        assert resp.status_code == 422

    def test_eva_generic(self, monkeypatch):
        from fusion_finance.modeling import valuation as val

        monkeypatch.setattr(val.EVAModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/eva", json={"company": "X", "nopat": [10], "invested_capital": [100]})
        assert resp.status_code == 422

    def test_ri_generic(self, monkeypatch):
        from fusion_finance.modeling import valuation as val

        monkeypatch.setattr(val.RIModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/ri", json={"company": "X", "book_value": 1, "net_income": [10]})
        assert resp.status_code == 422

    def test_portfolio_optimize_generic(self, monkeypatch):
        from fusion_finance.modeling import portfolio as pf

        monkeypatch.setattr(pf.PortfolioOptimizer, "efficient_frontier", staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/modeling/portfolio/optimize", json={"returns": [0.1]})
        assert resp.status_code == 422

    def test_frontier_sample_generic(self, monkeypatch):
        from fusion_finance.modeling import portfolio as pf

        monkeypatch.setattr(pf.PortfolioOptimizer, "efficient_frontier", staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.get("/api/v1/modeling/portfolio/frontier")
        assert resp.status_code == 422

    def test_create_session_generic(self, monkeypatch):
        from fusion_finance.api.routes import modeling as mod

        monkeypatch.setattr(mod.InteractiveDCFSession, "__init__", lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/session", json={"company": "X", "assumptions": {"wacc": 0.1}})
        assert resp.status_code == 422

    def test_update_session_not_found(self):
        c = _client()
        resp = c.put("/api/v1/modeling/session/nope", json={"key": "wacc", "value": 0.1})
        assert resp.status_code == 404

    def test_update_session_generic(self, monkeypatch):
        from fusion_finance.api.routes import modeling as mod

        c = _client()
        resp = c.post("/api/v1/modeling/session", json={"company": "X", "assumptions": {"wacc": 0.1}})
        sid = resp.json()["session_id"]
        monkeypatch.setattr(mod._sessions[sid]["session"], "update_assumption", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        resp = c.put(f"/api/v1/modeling/session/{sid}", json={"key": "wacc", "value": 0.12})
        assert resp.status_code == 422

    def test_scenario_generic(self, monkeypatch):
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.DCFModel, "calculate", lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/scenarios", json={"company": "X", "revenue": [100]})
        assert resp.status_code == 422

    def test_batch_dcf_generic(self, monkeypatch):
        from fusion_finance.modeling import engine as eng

        monkeypatch.setattr(eng.FinancialModelingEngine, "batch_dcf", staticmethod(lambda models: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/modeling/batch-dcf", json={"models": [{"company": "X", "revenue": [100]}]})
        assert resp.status_code == 422

    def test_black_litterman_generic(self, monkeypatch):
        from fusion_finance.modeling import portfolio as pf

        monkeypatch.setattr(pf.BlackLittermanOptimizer, "posterior_returns", staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/modeling/portfolio/black-litterman", json={"market_weights": [0.5, 0.5], "cov_matrix": [[1, 0], [0, 1]]})
        assert resp.status_code == 422

    def test_black_litterman_bad_params(self):
        c = _client()
        resp = c.post("/api/v1/modeling/portfolio/black-litterman", json={"market_weights": []})
        assert resp.status_code == 400

    def test_yield_curve_generic(self, monkeypatch):
        from fusion_finance.modeling import portfolio as pf

        monkeypatch.setattr(pf.YieldCurve, "nelson_siegel", lambda self, m: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/yield-curve", json={"maturities": [1.0]})
        assert resp.status_code == 422

    def test_yield_curve_calibrate_generic(self, monkeypatch):
        from fusion_finance.modeling import portfolio as pf

        monkeypatch.setattr(pf.YieldCurve, "calibrate", lambda self, *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/modeling/yield-curve/calibrate", json={"observed_maturities": [1, 2], "observed_rates": [0.03, 0.035]})
        assert resp.status_code == 422


# ---------- Risk route error branches ----------


class TestRiskRouteErrors:
    def test_kyc_risk_error(self):
        _mock_mlx(returns="not json")
        try:
            c = _client()
            resp = c.post("/api/v1/risk/kyc", json={"entity": "X", "jurisdiction": "CN"})
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_kyc_generic_error(self, monkeypatch):
        from fusion_finance.risk import engine as reng

        async def boom(self, *a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(reng.RiskComplianceEngine, "kyc_screening", boom)
        c = _client()
        resp = c.post("/api/v1/risk/kyc", json={"entity": "X"})
        assert resp.status_code == 422

    def test_credit_risk_error(self):
        _mock_mlx(returns="not json")
        try:
            c = _client()
            resp = c.post("/api/v1/risk/credit", json={"entity": "X", "financials": {"revenue": 100}})
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_credit_generic_error(self, monkeypatch):
        from fusion_finance.risk import engine as reng

        async def boom(self, *a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(reng.RiskComplianceEngine, "credit_assessment", boom)
        c = _client()
        resp = c.post("/api/v1/risk/credit", json={"entity": "X", "financials": {}})
        assert resp.status_code == 422

    def test_compliance_risk_error(self):
        _mock_mlx(returns="not json")
        try:
            c = _client()
            resp = c.post("/api/v1/risk/compliance", json={"contract": "C", "regulations": "R"})
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_compliance_generic_error(self, monkeypatch):
        from fusion_finance.risk import engine as reng

        async def boom(self, *a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(reng.RiskComplianceEngine, "compliance_check", boom)
        c = _client()
        resp = c.post("/api/v1/risk/compliance", json={"contract": "C"})
        assert resp.status_code == 422

    def test_var_generic_error(self, monkeypatch):
        from fusion_finance.risk import advanced_risk as ar

        monkeypatch.setattr(ar.RiskModelingEngine, "calculate_var", staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/risk/var", json={"returns": [0.1], "portfolio_value": 100})
        assert resp.status_code == 422

    def test_monte_carlo_var_generic_error(self, monkeypatch):
        from fusion_finance.risk import advanced_risk as ar

        monkeypatch.setattr(ar.RiskModelingEngine, "monte_carlo_var", staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/risk/var/monte-carlo", json={"portfolio_value": 100, "simulations": 5})
        assert resp.status_code == 422

    def test_stress_scenarios_generic_error(self, monkeypatch):
        from fusion_finance.risk import advanced_risk as ar

        monkeypatch.setattr(ar.RiskModelingEngine, "stress_test_scenarios", staticmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.get("/api/v1/risk/stress-scenarios")
        assert resp.status_code == 422

    def test_stress_test_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import risk as rroute

        monkeypatch.setattr(rroute, "asdict", lambda x: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/risk/stress-test", json={"scenario": "x", "impact": 0.1})
        assert resp.status_code == 422

    def test_sanctions_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import risk as rroute

        monkeypatch.setattr(rroute._sanctions_engine, "screen", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/risk/sanctions", json={"entity": "x"})
        assert resp.status_code == 422

    def test_sanctions_batch_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import risk as rroute

        monkeypatch.setattr(rroute._sanctions_engine, "screen_batch", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/risk/sanctions/batch", json={"entities": ["a"]})
        assert resp.status_code == 422

    def test_entity_graph_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import risk as rroute

        monkeypatch.setattr(rroute._entity_resolver, "build_from_structure", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/risk/entity-graph", json={"nodes": [], "edges": []})
        assert resp.status_code == 422

    def test_resolve_ubo_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import risk as rroute

        monkeypatch.setattr(rroute._entity_resolver, "build_from_structure", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/risk/entity-graph/ubo", json={"target_entity_id": "x"})
        assert resp.status_code == 422


# ---------- Data route error branches ----------


class TestDataRouteErrors:
    def test_import_non_utf8(self):
        c = _client()
        resp = c.post(
            "/api/v1/data/import",
            files={"file": ("r.csv", b"\xff\xfe\x00\x01binary", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_import_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._adapter, "load_csv", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post(
            "/api/v1/data/import",
            files={"file": ("r.csv", b"a,b\n1,2\n", "text/csv")},
        )
        assert resp.status_code == 400

    def test_import_valid_csv(self):
        c = _client()
        resp = c.post(
            "/api/v1/data/import",
            files={"file": ("r.csv", b"a,b\n1,2\n3,4\n", "text/csv")},
        )
        assert resp.status_code == 200

    def test_validate_balance_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._adapter, "validate_balance", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/data/validate/balance", json={"assets": 1, "liabilities": 1, "equity": 1})
        assert resp.status_code == 400

    def test_check_completeness_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._adapter, "check_completeness", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/data/validate/completeness", json={"data": [{"a": 1}]})
        assert resp.status_code == 400

    def test_list_cache_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute, "CACHE_DIR", MagicMock(spec=Path))
        droute.CACHE_DIR.exists = MagicMock(side_effect=RuntimeError("boom"))
        c = _client()
        resp = c.get("/api/v1/data/cache")
        assert resp.status_code == 400

    def test_delete_cache_unsafe_key(self):
        c = _client()
        resp = c.delete("/api/v1/data/cache/a..b")
        assert resp.status_code == 400

    def test_delete_cache_not_found(self):
        c = _client()
        resp = c.delete("/api/v1/data/cache/csv_nonexistent")
        assert resp.status_code == 404

    def test_delete_cache_ok(self):
        c = _client()
        # import then delete
        c.post("/api/v1/data/import", files={"file": ("r.csv", b"a,b\n1,2\n", "text/csv")})
        items = c.get("/api/v1/data/cache").json()["items"]
        if items:
            resp = c.delete(f"/api/v1/data/cache/{items[0]['key']}")
            assert resp.status_code == 200

    def test_market_quotes_ok(self):
        c = _client()
        resp = c.get("/api/v1/data/market/quotes", params={"market": "HK"})
        assert resp.status_code == 200

    def test_market_quotes_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._market, "get_quotes", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.get("/api/v1/data/market/quotes")
        assert resp.status_code == 400

    def test_market_ohlcv_ok(self):
        c = _client()
        resp = c.post("/api/v1/data/market/ohlcv", json={"symbol": "00700", "base_price": 300, "bars": 10})
        assert resp.status_code == 200

    def test_market_ohlcv_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._market, "get_ohlcv", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/data/market/ohlcv", json={"symbol": "x"})
        assert resp.status_code == 400

    def test_market_technicals_ok(self):
        c = _client()
        ohlcv = c.post("/api/v1/data/market/ohlcv", json={"symbol": "x", "base_price": 100, "bars": 60}).json()["ohlcv"]
        resp = c.post("/api/v1/data/market/technicals", json={"ohlcv": ohlcv})
        assert resp.status_code == 200

    def test_market_technicals_generic_error(self, monkeypatch):
        from fusion_finance.api.routes import data as droute

        monkeypatch.setattr(droute._market, "compute_technicals", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/data/market/technicals", json={"ohlcv": []})
        assert resp.status_code == 400


# ---------- Report route error branches ----------


class TestReportRouteErrors:
    def test_research_generic_error(self, monkeypatch):
        from fusion_finance.report import reports as rep

        async def boom(self, *a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(rep.ReportGenerator, "generate_research_report", boom)
        c = _client()
        resp = c.post("/api/v1/report/research", json={"company": "X", "industry": "T", "data": {}})
        assert resp.status_code == 500

    def test_research_ai_error(self):
        _mock_mlx(raises=RuntimeError("ai down"))
        try:
            c = _client()
            resp = c.post("/api/v1/report/research", json={"company": "X", "industry": "T", "data": {}})
            assert resp.status_code == 503
        finally:
            app.dependency_overrides.clear()

    def test_export_unsupported_format_error(self):
        c = _client()
        resp = c.post("/api/v1/report/export/docx", json={"content": "x", "name": "r"})
        assert resp.status_code == 400

    def test_export_pdf_ok(self):
        c = _client()
        resp = c.post("/api/v1/report/export/pdf", json={"content": "<h1>x</h1>", "name": "rpdf"})
        assert resp.status_code == 200

    def test_export_xlsx_ok(self):
        c = _client()
        resp = c.post("/api/v1/report/export/xlsx", json={"content": "a,b\n1,2", "name": "rx"})
        assert resp.status_code == 200

    def test_export_pptx_ok(self):
        c = _client()
        resp = c.post("/api/v1/report/export/pptx", json={"content": "hello", "name": "rp"})
        assert resp.status_code == 200

    def test_export_empty_name_ok(self):
        c = _client()
        resp = c.post("/api/v1/report/export/html", json={"content": "x", "name": ""})
        assert resp.status_code == 200


# ---------- Statements route error branches ----------


class TestStatementsRouteErrors:
    def test_analyze_generic_error(self, monkeypatch):
        from fusion_finance.statements import analyzer as anz

        async def boom(self, *a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(anz.StatementAnalyzer, "analyze_statements", boom)
        c = _client()
        resp = c.post("/api/v1/statements/analyze", json={"company": "X", "data": {"revenue": 100}})
        assert resp.status_code == 400

    def test_analyze_report_error(self):
        _mock_mlx(raises=RuntimeError("ai down"))
        try:
            c = _client()
            resp = c.post("/api/v1/statements/analyze", json={"company": "X", "data": {}})
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()

    def test_metrics_generic_error(self, monkeypatch):
        from fusion_finance.statements import analyzer as anz

        monkeypatch.setattr(anz.StatementAnalyzer, "calculate_metrics", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/statements/metrics", json={"company": "X", "revenue": 1, "net_income": 1, "total_assets": 1})
        assert resp.status_code == 400

    def test_validate_generic_error(self, monkeypatch):
        from fusion_finance.statements import analyzer as anz

        monkeypatch.setattr(anz.StatementAnalyzer, "validate_balance_sheet", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/statements/validate", json={"statements": [{"company": "X", "total_assets": 1, "total_liabilities": 0, "equity": 1}]})
        assert resp.status_code == 400

    def test_screener_generic_error(self, monkeypatch):
        from fusion_finance.statements import screener as scr

        monkeypatch.setattr(scr.FinancialScreener, "screen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/statements/screener", json={"filters": {"preset": "growth"}, "limit": 5})
        assert resp.status_code == 400

    def test_normalize_generic_error(self, monkeypatch):
        from fusion_finance.statements import normalizer as norm

        monkeypatch.setattr(norm.StatementNormalizer, "normalize", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        c = _client()
        resp = c.post("/api/v1/statements/normalize", json={"data": {"revenue": 1}, "standard": "A", "company": "X"})
        assert resp.status_code == 400

    def test_trend_generic_error(self, monkeypatch):
        from fusion_finance.statements import normalizer as norm

        monkeypatch.setattr(norm.StatementNormalizer, "trend_analysis", staticmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))))
        c = _client()
        resp = c.post("/api/v1/statements/trend", json={"statements": [{"company": "X", "period": "2024", "revenue": 1}]})
        assert resp.status_code == 400


# ---------- Audit route coverage ----------


class TestAuditRouteCov:
    def test_query_ok(self):
        c = _client()
        assert c.get("/api/v1/audit/entries", params={"limit": 5}).status_code in (200, 404)

    def test_stats_ok(self):
        c = _client()
        assert c.get("/api/v1/audit/stats").status_code == 200

    def test_file_stats_ok(self):
        c = _client()
        assert c.get("/api/v1/audit/stats?source=file").status_code == 200

    def test_verify_ok(self):
        c = _client()
        assert c.get("/api/v1/audit/verify").status_code in (200, 404)

    def test_export_ok(self):
        c = _client()
        assert c.get("/api/v1/audit/export").status_code in (200, 404)


# ---------- Formatter unit error branches ----------


class TestFormatterErrors:
    def test_render_html_template_render_fail(self, monkeypatch):
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        # force jinja env present, then break get_template
        f._jinja_env = MagicMock()
        f._jinja_env.get_template.side_effect = RuntimeError("boom")
        out = f.render_html("valuation", {"company": "X"})
        assert "X" in out or "Unknown" in out

    def test_render_html_no_jinja_fallback(self, monkeypatch):
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        f._jinja_env = False
        out = f.render_html("valuation", {"company": "CoZ", "content": "hello"})
        assert "CoZ" in out

    def test_export_pdf_weasyprint_fail(self, monkeypatch):
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        if f._weasyprint is None:
            pytest.skip("weasyprint not installed")
        bad = MagicMock()
        bad.HTML.side_effect = RuntimeError("pdf boom")
        f._weasyprint = bad

        ret = f.export("<h1>x</h1>", "pdf", "pdfx")
        assert ret.endswith(".html")

    def test_export_pptx_fail_fallback_txt(self, monkeypatch):
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        if f._pptx is None:
            pytest.skip("pptx not installed")
        bad_prs = MagicMock()
        bad_prs.return_value.slides.add_slide.side_effect = RuntimeError("pptx boom")
        f._pptx = bad_prs
        ret = f.export("hello", "pptx", "pptxx")
        assert ret.endswith(".txt")

    def test_export_xlsx_fail_fallback_csv(self, monkeypatch):
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        if f._openpyxl is None:
            pytest.skip("openpyxl not installed")
        bad_wb = MagicMock()
        bad_wb.Workbook.return_value.active.append.side_effect = RuntimeError("xlsx boom")
        f._openpyxl = bad_wb
        ret = f.export("a,b\n1,2", "xlsx", "xlsxx")
        assert ret.endswith(".csv")

    def test_export_invalid_path(self):
        from fusion_finance.exceptions import ReportError
        from fusion_finance.report import formatter as fmt

        f = fmt.ReportFormatter()
        with pytest.raises(ReportError):
            f.export("x", "html", "..")


# ---------- Normalizer unit branches ----------


class TestNormalizerCov:
    def test_normalize_unknown_standard(self):
        from fusion_finance.statements.normalizer import StatementNormalizer

        n = StatementNormalizer(standard="ZZZ")
        out = n.normalize({"total_revenue": 100}, company="X")
        assert out.company == "X"
        assert out.revenue == 100.0

    def test_normalize_multi_transient_standard(self):
        from fusion_finance.statements.normalizer import StatementNormalizer

        n = StatementNormalizer(standard="A")
        out = n.normalize_multi([{"revenue": 100}, {"revenue": 200}], standard="IFRS")
        assert isinstance(out, list)

    def test_list_standards(self):
        from fusion_finance.statements.normalizer import StatementNormalizer

        out = StatementNormalizer.list_standards()
        assert isinstance(out, list)
        assert len(out) > 0
