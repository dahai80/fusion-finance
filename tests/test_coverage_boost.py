"""Coverage-boost tests targeting low-coverage modules for enterprise release gate."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from fusion_finance.api.app import app
from fusion_finance.api.routes import modeling as modeling_route


@pytest.fixture(autouse=True)
def _restore_config():
    from fusion_finance import config

    snapshot = {
        "DATA_DIR": config.DATA_DIR,
        "AUDIT_DIR": config.AUDIT_DIR,
        "PROJECT_DIR": config.PROJECT_DIR,
        "CACHE_DIR": config.CACHE_DIR,
        "EXPORT_DIR": config.EXPORT_DIR,
    }
    yield
    for k, v in snapshot.items():
        setattr(config, k, v)


def _client() -> TestClient:
    return TestClient(app)


class TestParseJson:
    def test_none_and_empty(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json(None) is None
        assert parse_json("") is None
        assert parse_json("   ") is None
        assert parse_json(123) is None

    def test_plain_json(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json('{"a": 1}') == {"a": 1}
        assert parse_json("[1, 2, 3]") == [1, 2, 3]

    def test_fenced_json(self):
        from fusion_finance.utils.parse_json import parse_json

        text = "```json\n{\"a\": 1}\n```"
        assert parse_json(text) == {"a": 1}
        text2 = "```\n[1, 2]\n```"
        assert parse_json(text2) == [1, 2]

    def test_embedded_object(self):
        from fusion_finance.utils.parse_json import parse_json

        text = "Here is the result: {\"a\": 1, \"b\": 2} done"
        assert parse_json(text) == {"a": 1, "b": 2}

    def test_embedded_array(self):
        from fusion_finance.utils.parse_json import parse_json

        text = "Result: [1, 2, 3] end"
        assert parse_json(text) == [1, 2, 3]

    def test_balanced_with_strings(self):
        from fusion_finance.utils.parse_json import parse_json

        text = 'noise {"a": "x}y", "b": {"c": 1}} tail'
        assert parse_json(text) == {"a": "x}y", "b": {"c": 1}}

    def test_multiple_objects_warns_first(self):
        from fusion_finance.utils.parse_json import parse_json

        text = '{"a": 1} {"b": 2}'
        result = parse_json(text)
        assert result == {"a": 1}

    def test_invalid_returns_none(self):
        from fusion_finance.utils.parse_json import parse_json

        assert parse_json("not json at all") is None
        assert parse_json("{broken") is None

    def test_large_text_balanced(self):
        from fusion_finance.utils.parse_json import _MAX_PARSE_LEN, parse_json

        payload = '{"a": 1, "b": [1, 2, 3]}' + " " * (_MAX_PARSE_LEN + 100)
        assert parse_json(payload) == {"a": 1, "b": [1, 2, 3]}

    def test_large_invalid_returns_none(self):
        from fusion_finance.utils.parse_json import _MAX_PARSE_LEN, parse_json

        payload = "x" * (_MAX_PARSE_LEN + 100)
        assert parse_json(payload) is None

    def test_hard_cap_returns_none(self):
        from fusion_finance.utils.parse_json import _HARD_CAP_LEN, parse_json

        payload = "x" * (_HARD_CAP_LEN + 1)
        assert parse_json(payload) is None

    def test_extract_all_json(self):
        from fusion_finance.utils.parse_json import extract_all_json

        text = 'pre {"a": 1} mid {"b": 2} post'
        assert extract_all_json(text) == [{"a": 1}, {"b": 2}]
        assert extract_all_json(None) == []
        assert extract_all_json("") == []
        assert extract_all_json("no json") == []

    def test_extract_all_json_hard_cap(self):
        from fusion_finance.utils.parse_json import _HARD_CAP_LEN, extract_all_json

        text = "x" * (_HARD_CAP_LEN + 1)
        assert extract_all_json(text) == []

    def test_extract_all_json_invalid_skipped(self):
        from fusion_finance.utils.parse_json import extract_all_json

        text = '{"a": 1} {broken} {"b": 2}'
        assert extract_all_json(text) == [{"a": 1}, {"b": 2}]

    def test_escape_handling(self):
        from fusion_finance.utils.parse_json import parse_json

        text = r'{"a": "he said \"hi\""}'
        assert parse_json(text) == {"a": 'he said "hi"'}


class TestConfigAuth:
    def test_is_auth_disabled(self, monkeypatch):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        assert config.is_auth_disabled() is True
        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        assert config.is_auth_disabled() is False

    def test_is_loopback_host(self):
        from fusion_finance import config

        assert config.is_loopback_host("127.0.0.1") is True
        assert config.is_loopback_host("localhost") is True
        assert config.is_loopback_host("::1") is True
        assert config.is_loopback_host("0.0.0.0") is False

    def test_auth_safety_loopback_warns(self, monkeypatch):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        warnings = config.auth_safety_check("127.0.0.1")
        assert len(warnings) == 1
        assert "local loopback" in warnings[0]

    def test_auth_safety_nonloopback_refuses(self, monkeypatch):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        warnings = config.auth_safety_check("0.0.0.0")
        assert len(warnings) == 1
        assert "Refusing to start" in warnings[0]

    def test_auth_safety_enabled_empty(self, monkeypatch):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        assert config.auth_safety_check("0.0.0.0") == []

    def test_get_api_key_disabled(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        assert config.get_api_key() == ""

    def test_get_api_key_explicit_env(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "explicit-key-123")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        assert config.get_api_key() == "explicit-key-123"

    def test_get_api_key_generated(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        monkeypatch.delenv("FUSION_FINANCE_API_KEY", raising=False)
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        key = config.get_api_key()
        assert key and len(key) > 10
        assert (tmp_path / "api_key").exists()

    def test_verify_api_key(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "secret-key")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        assert config.verify_api_key("secret-key") is True
        assert config.verify_api_key("wrong") is False
        assert config.verify_api_key("") is False

    def test_verify_api_key_disabled(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        assert config.verify_api_key("anything") is True

    def test_get_cors_origins(self, monkeypatch):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_CORS_ORIGINS", "http://a.com, http://b.com")
        assert config.get_cors_origins() == ["http://a.com", "http://b.com"]
        monkeypatch.setenv("FUSION_FINANCE_CORS_ORIGINS", "")
        assert config.get_cors_origins() == ["http://127.0.0.1", "http://localhost"]

    def test_setup_logging(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        config.setup_logging("DEBUG")
        config.setup_logging("DEBUG")
        assert (tmp_path / "fusion-finance.log").parent.exists()

    def test_load_runtime_config(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "1")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        rc = config.load_runtime_config()
        assert "host" in rc and "port" in rc and "cors_origins" in rc
        assert isinstance(config.dump_runtime_config(), str)

    def test_ensure_dirs(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        config.AUDIT_DIR = tmp_path / "audit"
        config.PROJECT_DIR = tmp_path / "projects"
        config.CACHE_DIR = tmp_path / "cache"
        config.EXPORT_DIR = tmp_path / "exports"
        config.ensure_dirs()
        assert config.AUDIT_DIR.exists()


class TestVersionControl:
    def test_compute_hash(self):
        from fusion_finance.project.version import VersionControl

        h1 = VersionControl.compute_hash({"a": 1, "b": 2})
        h2 = VersionControl.compute_hash({"b": 2, "a": 1})
        assert h1 == h2
        assert len(h1) == 16

    def test_diff_added_removed_changed(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1, "b": 99, "d": 4}
        d = vc.diff(old, new)
        assert d["added"] == {"d": 4}
        assert d["removed"] == {"c": 3}
        assert d["changed"] == {"b": {"old": 2, "new": 99}}

    def test_diff_nested_dicts(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"obj": {"x": 1, "y": 2}}
        new = {"obj": {"x": 1, "y": 99, "z": 3}}
        d = vc.diff(old, new)
        assert "obj.y" in d["changed"]
        assert "obj.z" in d["changed"]

    def test_diff_lists(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 99, 3, 4]}
        d = vc.diff(old, new)
        assert "items[1]" in d["changed"]
        assert "items[3]" in d["changed"]

    def test_diff_list_shrinks(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"items": [1, 2, 3]}
        new = {"items": [1]}
        d = vc.diff(old, new)
        assert "items[1]" in d["changed"]
        assert "items[2]" in d["changed"]

    def test_patch_applies(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"a": 1, "b": 2}
        new = {"a": 1, "b": 99, "c": 3}
        d = vc.diff(old, new)
        patched = vc.patch(old, d)
        assert patched["b"] == 99
        assert patched["c"] == 3
        assert "a" in patched

    def test_patch_removes_key(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        d = vc.diff(old, new)
        patched = vc.patch(old, d)
        assert "b" not in patched

    def test_patch_nested_path(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"obj": {"x": 1, "y": 2}}
        new = {"obj": {"x": 1, "y": 99}}
        d = vc.diff(old, new)
        patched = vc.patch(old, d)
        assert patched["obj"]["y"] == 99

    def test_cherry_pick(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        versions = [
            {"version": 1, "data": {"a": 1}},
            {"version": 2, "data": {"a": 2}},
        ]
        assert vc.cherry_pick(versions, 2) == {"a": 2}
        assert vc.cherry_pick(versions, 99) is None

    def test_history_summary(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        versions = [
            {"version": 1, "data": {"a": 1}, "label": "v1", "timestamp": 100},
            {"version": 2, "data": {"a": 2}, "label": "v2", "timestamp": 200},
        ]
        summary = vc.history_summary(versions)
        assert len(summary) == 2
        assert summary[0]["version"] == 1
        assert "changes" in summary[1]
        assert summary[1]["changes"]["changed"] == 1

    def test_patch_list_path_set(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 99, 3]}
        d = vc.diff(old, new)
        patched = vc.patch(old, d)
        assert patched["items"][1] == 99

    def test_patch_list_path_unset(self):
        from fusion_finance.project.version import VersionControl

        vc = VersionControl()
        base = {"items": [1, 2, 3], "obj": {"k": "v"}}
        diff_result = {"added": {}, "removed": {}, "changed": {"items[1]": {"old": 2, "new": "__removed__"}}}
        patched = vc.patch(base, diff_result)
        assert patched["items"][1] is None

    def test_tokenize_variants(self):
        from fusion_finance.project.version import VersionControl

        assert VersionControl._tokenize("a.b.c") == ["a", "b", "c"]
        assert VersionControl._tokenize("a[0].b[1]") == ["a", 0, "b", 1]
        assert VersionControl._tokenize("a[x]") == ["a", "x"]
        assert VersionControl._tokenize("a[") == ["a"]
        assert VersionControl._tokenize("") == []

    def test_set_path_descend_none(self):
        from fusion_finance.project.version import VersionControl

        data = {"a": 1}
        VersionControl._set_path(data, "x.y.z", 99)
        assert data == {"a": 1}

    def test_unset_path_descend_none(self):
        from fusion_finance.project.version import VersionControl

        data = {"a": 1}
        VersionControl._unset_path(data, "x.y.z")
        assert data == {"a": 1}

    def test_descend_oob(self):
        from fusion_finance.project.version import VersionControl

        assert VersionControl._descend([1, 2], 5) is None
        assert VersionControl._descend({"a": 1}, "b") is None
        assert VersionControl._descend("str", 0) is None

    def test_set_path_empty_tokens(self):
        from fusion_finance.project.version import VersionControl

        data = {"a": 1}
        VersionControl._set_path(data, "", 99)
        assert data == {"a": 1}


class TestModelingRoutes:
    def test_monte_carlo_route(self):
        c = _client()
        payload = {
            "company": "Test",
            "revenue": [100, 120, 140],
            "ebit_margin": [0.2, 0.22, 0.25],
            "simulations": 50,
        }
        resp = c.post("/api/v1/modeling/monte-carlo", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "simulations" in data

    def test_efficient_frontier_sample(self):
        c = _client()
        resp = c.get("/api/v1/modeling/portfolio/frontier")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample"] is True
        assert data["deprecated"] is True

    def test_session_create_update(self):
        c = _client()
        resp = c.post("/api/v1/modeling/session", json={"company": "Test", "assumptions": {"wacc": 0.1}})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        resp2 = c.put(f"/api/v1/modeling/session/{sid}", json={"key": "wacc", "value": 0.12})
        assert resp2.status_code == 200

    def test_session_update_not_found(self):
        c = _client()
        resp = c.put("/api/v1/modeling/session/nonexistent", json={"key": "wacc", "value": 0.12})
        assert resp.status_code == 404

    def test_black_litterman_route(self):
        c = _client()
        payload = {
            "market_weights": [0.5, 0.5],
            "cov_matrix": [[0.04, 0.01], [0.01, 0.09]],
            "risk_aversion": 2.5,
        }
        resp = c.post("/api/v1/modeling/portfolio/black-litterman", json=payload)
        assert resp.status_code == 200

    def test_black_litterman_bad_params(self):
        c = _client()
        payload = {"market_weights": [], "cov_matrix": []}
        resp = c.post("/api/v1/modeling/portfolio/black-litterman", json=payload)
        assert resp.status_code in (400, 422)

    def test_yield_curve_route(self):
        c = _client()
        payload = {"maturities": [1, 2, 5, 10], "beta0": 0.04}
        resp = c.post("/api/v1/modeling/yield-curve", json=payload)
        assert resp.status_code == 200
        assert "rates" in resp.json()

    def test_yield_curve_calibrate_route(self):
        c = _client()
        payload = {"observed_maturities": [1, 2, 5, 10], "observed_rates": [0.03, 0.035, 0.04, 0.045]}
        resp = c.post("/api/v1/modeling/yield-curve/calibrate", json=payload)
        assert resp.status_code == 200

    def test_build_dcf_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(return_value='{"ebit_margin": [0.2, 0.22, 0.25], "tax_rate": 0.25, "wacc": 0.1}')
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/modeling/dcf", json={"company": "Test", "revenue": [100, 120, 140]})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_build_comps_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(return_value='{"peers": ["A", "B"], "avg_pe": 15, "avg_ev_ebitda": 8}')
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/modeling/comps", json={"company": "Test", "industry": "科技"})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_lbo_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(return_value='{"entry_ev": 1000, "exit_ev": 1500, "irr": 0.25}')
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/modeling/lbo", json={"company": "Test", "ebitda": [100, 120, 140]})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestSessionPrune:
    def test_prune_stale_sessions(self):
        modeling_route._sessions.clear()
        modeling_route._sessions["old"] = {
            "session": MagicMock(),
            "created_at": time.time() - 7200,
            "last_active": time.time() - 7200,
        }
        modeling_route._sessions["fresh"] = {
            "session": MagicMock(),
            "created_at": time.time(),
            "last_active": time.time(),
        }
        modeling_route._prune_sessions()
        assert "old" not in modeling_route._sessions
        assert "fresh" in modeling_route._sessions
        modeling_route._sessions.clear()

    def test_prune_over_cap(self):
        modeling_route._sessions.clear()
        for i in range(modeling_route._MAX_SESSIONS + 10):
            modeling_route._sessions[f"s{i}"] = {
                "session": MagicMock(),
                "created_at": time.time(),
                "last_active": time.time() + i,
            }
        modeling_route._prune_sessions()
        assert len(modeling_route._sessions) <= modeling_route._MAX_SESSIONS
        modeling_route._sessions.clear()


class TestRiskRoutes:
    def test_kyc_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(
            return_value='{"risk_level": "low", "risk_score": 80, "findings": [], "recommendations": []}'
        )
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/risk/kyc", json={"entity": "TestCorp"})
            assert resp.status_code == 200
            assert resp.json()["risk_level"] == "low"
        finally:
            app.dependency_overrides.clear()

    def test_credit_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(
            return_value='{"credit_score": 75, "rating": "A", "max_credit_line": 5000, "strengths": [], "concerns": []}'
        )
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/risk/credit", json={"entity": "TestCorp", "financials": {"revenue": 1000}})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_compliance_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(
            return_value='{"compliant": true, "issues": [], "overall_risk": "low", "summary": "ok"}'
        )
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/risk/compliance", json={"contract": "test contract"})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_monte_carlo_var_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/risk/var/monte-carlo",
            json={"portfolio_value": 1000000, "mu": 0.08, "sigma": 0.20, "days": 252, "simulations": 1000},
        )
        assert resp.status_code == 200

    def test_stress_test_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/risk/stress-test",
            json={"scenario": "market crash", "impact": -0.2, "affected_factors": ["equity"]},
        )
        assert resp.status_code == 200

    def test_sanctions_route(self):
        c = _client()
        resp = c.post("/api/v1/risk/sanctions", json={"entity": "test entity", "threshold": 0.5})
        assert resp.status_code == 200

    def test_entity_graph_route(self):
        c = _client()
        payload = {
            "nodes": [{"id": "n1", "name": "A", "type": "company"}],
            "edges": [],
        }
        resp = c.post("/api/v1/risk/entity-graph", json=payload)
        assert resp.status_code == 200


class TestRiskEngineFallback:
    @pytest.mark.asyncio
    async def test_kyc_empty_response_raises(self):
        from fusion_finance.exceptions import RiskError
        from fusion_finance.risk.engine import RiskComplianceEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="not parseable")
        engine = RiskComplianceEngine(mlx=mlx)
        with pytest.raises(RiskError):
            await engine.kyc_screening("TestCorp")

    @pytest.mark.asyncio
    async def test_kyc_chat_error_raises(self):
        from fusion_finance.exceptions import RiskError
        from fusion_finance.risk.engine import RiskComplianceEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(side_effect=RuntimeError("mlx down"))
        engine = RiskComplianceEngine(mlx=mlx)
        with pytest.raises(RiskError):
            await engine.kyc_screening("TestCorp")

    @pytest.mark.asyncio
    async def test_credit_empty_response_raises(self):
        from fusion_finance.exceptions import RiskError
        from fusion_finance.risk.engine import RiskComplianceEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="")
        engine = RiskComplianceEngine(mlx=mlx)
        with pytest.raises(RiskError):
            await engine.credit_assessment("TestCorp", {"revenue": 1000})

    @pytest.mark.asyncio
    async def test_compliance_empty_response_raises(self):
        from fusion_finance.exceptions import RiskError
        from fusion_finance.risk.engine import RiskComplianceEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="garbage")
        engine = RiskComplianceEngine(mlx=mlx)
        with pytest.raises(RiskError):
            await engine.compliance_check("contract text")

    @pytest.mark.asyncio
    async def test_compliance_long_contract(self):
        from fusion_finance.risk.engine import RiskComplianceEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value='{"compliant": true, "issues": [], "overall_risk": "low", "summary": "ok"}')
        engine = RiskComplianceEngine(mlx=mlx)
        result = await engine.compliance_check("x" * 6000)
        assert result["compliant"] is True


class TestDataRoutes:
    def test_validate_balance_ok(self):
        c = _client()
        resp = c.post("/api/v1/data/validate/balance", json={"assets": 1000, "liabilities": 400, "equity": 600})
        assert resp.status_code == 200

    def test_validate_balance_off(self):
        c = _client()
        resp = c.post("/api/v1/data/validate/balance", json={"assets": 1000, "liabilities": 400, "equity": 100})
        assert resp.status_code == 200

    def test_completeness(self):
        c = _client()
        resp = c.post(
            "/api/v1/data/validate/completeness",
            json={"data": [{"a": 1, "b": 2}, {"a": 1}], "required_fields": ["a", "b"]},
        )
        assert resp.status_code == 200

    def test_market_quotes(self):
        c = _client()
        resp = c.get("/api/v1/data/market/quotes", params={"market": "A"})
        assert resp.status_code == 200

    def test_market_ohlcv(self):
        c = _client()
        resp = c.post("/api/v1/data/market/ohlcv", json={"symbol": "600519", "base_price": 100, "bars": 30})
        assert resp.status_code == 200

    def test_market_technicals(self):
        c = _client()
        ohlcv = [{"open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000} for _ in range(30)]
        resp = c.post("/api/v1/data/market/technicals", json={"ohlcv": ohlcv})
        assert resp.status_code == 200

    def test_cache_list_and_delete(self):
        c = _client()
        resp = c.get("/api/v1/data/cache")
        assert resp.status_code == 200
        resp2 = c.delete("/api/v1/data/cache/nonexistent_key")
        assert resp2.status_code == 404

    def test_cache_delete_unsafe_key(self):
        c = _client()
        resp = c.delete("/api/v1/data/cache/a..b")
        assert resp.status_code == 400

    def test_import_csv(self):
        c = _client()
        csv_content = "name,value\nA,1\nB,2\n"
        resp = c.post(
            "/api/v1/data/import",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rows"] == 2


class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_publish(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("test-ch")
        assert q is not None
        await bus.publish("test-ch", {"msg": "hello"})
        data = await asyncio.wait_for(q.get(), timeout=1.0)
        assert json.loads(data)["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_subscriber_cap(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        for _ in range(bus.MAX_SUBSCRIBERS_PER_CHANNEL):
            assert bus.subscribe("cap-ch") is not None
        assert bus.subscribe("cap-ch") is None

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("uns-ch")
        bus.unsubscribe("uns-ch", q)
        await bus.publish("uns-ch", {"msg": "x"})
        assert q.qsize() == 0

    @pytest.mark.asyncio
    async def test_publish_queue_full(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        q = bus.subscribe("full-ch")
        for i in range(bus.MAX_QUEUE_SIZE):
            await bus.publish("full-ch", {"i": i})
        await bus.publish("full-ch", {"i": 999})
        assert q.qsize() == bus.MAX_QUEUE_SIZE

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self):
        from fusion_finance.api.sse import EventBus

        bus = EventBus()
        await bus.publish("empty-ch", {"msg": "x"})

    def test_publish_endpoint_no_key(self):
        c = _client()
        resp = c.post("/events/publish", params={"channel": "test"}, json={"msg": "hello"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    def test_publish_with_valid_key(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "sekret")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        c = _client()
        resp = c.post(
            "/events/publish",
            params={"channel": "test"},
            json={"msg": "hello"},
            headers={"x-api-key": "sekret"},
        )
        assert resp.status_code == 200

    def test_publish_invalid_key_rejected(self, monkeypatch, tmp_path):
        from fusion_finance import config

        monkeypatch.setenv("FUSION_FINANCE_DISABLE_AUTH", "0")
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "sekret")
        monkeypatch.setenv("FUSION_FINANCE_DATA_DIR", str(tmp_path))
        config.DATA_DIR = tmp_path
        c = _client()
        resp = c.post(
            "/events/publish",
            params={"channel": "test"},
            json={"msg": "hello"},
            headers={"x-api-key": "wrong"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_stream_emits_data_and_keepalive(self):
        import asyncio as _asyncio

        from fusion_finance.api.sse import _sse_stream

        q: asyncio.Queue = asyncio.Queue()
        await q.put('{"msg": "hello"}')
        gen = _sse_stream(q, keepalive_interval=0)
        first = await _asyncio.wait_for(gen.__anext__(), timeout=2.0)
        assert first.startswith("data: ")
        second = await _asyncio.wait_for(gen.__anext__(), timeout=3.0)
        assert second == ": keepalive\n\n"
        await gen.aclose()

    @pytest.mark.asyncio
    async def test_sse_stream_cancelled(self):
        import asyncio as _asyncio

        from fusion_finance.api.sse import _sse_stream

        q: asyncio.Queue = asyncio.Queue()
        gen = _sse_stream(q, keepalive_interval=999)
        task = _asyncio.create_task(gen.__anext__())
        await _asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, GeneratorExit, StopAsyncIteration):
            await task

    def test_insights_subscriber_cap_reject(self):
        from fusion_finance.api.sse import event_bus

        c = _client()
        held = []
        try:
            for _ in range(event_bus.MAX_SUBSCRIBERS_PER_CHANNEL):
                held.append(event_bus.subscribe("insights:captest"))
            resp = c.get("/events/insights", params={"session_id": "captest"})
            assert resp.status_code == 429
        finally:
            for q in held:
                event_bus.unsubscribe("insights:captest", q)


class TestCopilotEngine:
    @pytest.mark.asyncio
    async def test_chat_direct_answer(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="This is a direct answer")
        engine = CopilotEngine(mlx=mlx)
        result = await engine.chat("hello", session_id="sess1")
        assert result["reply"] == "This is a direct answer"
        assert result["rounds"] == 0

    @pytest.mark.asyncio
    async def test_chat_with_history(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="answer")
        engine = CopilotEngine(mlx=mlx)
        result = await engine.chat(
            "hello",
            session_id="sess2",
            history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}],
        )
        assert result["reply"] == "answer"

    @pytest.mark.asyncio
    async def test_chat_tool_call_then_final(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(
            side_effect=[
                '{"tool": "calculate_dcf", "args": {"company": "X", "revenue": [100, 120]}}',
                "non-tool intermediate",
                "Final synthesized answer",
            ]
        )
        registry = MagicMock()
        registry.execute = AsyncMock(return_value={"enterprise_value": 1000})
        registry.format_prompt.return_value = ""
        engine = CopilotEngine(mlx=mlx, registry=registry)
        result = await engine.chat("value X", session_id="sess3")
        assert result["rounds"] == 1
        assert result["tool_calls"]

    @pytest.mark.asyncio
    async def test_chat_tool_batch_calls(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(
            side_effect=[
                '{"tool_calls": [{"tool": "calculate_dcf", "args": {}}, {"tool": "bad_tool", "args": {}}]}',
                "non-tool intermediate",
                "Final answer",
            ]
        )
        registry = MagicMock()
        registry.execute = AsyncMock(side_effect=[{"ok": True}, RuntimeError("no such tool")])
        registry.format_prompt.return_value = ""
        engine = CopilotEngine(mlx=mlx, registry=registry)
        result = await engine.chat("batch", session_id="sess4")
        assert result["rounds"] == 1

    @pytest.mark.asyncio
    async def test_chat_reserved_session_id(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value="answer")
        engine = CopilotEngine(mlx=mlx)
        result = await engine.chat("hello", session_id="default")
        assert result["session_id"] != "default"

    @pytest.mark.asyncio
    async def test_chat_stream_direct(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()

        async def fake_stream(messages, **kwargs):
            yield "chunk1"
            yield "chunk2"

        mlx.chat_stream = fake_stream
        engine = CopilotEngine(mlx=mlx)
        chunks = []
        async for c in engine.chat_stream("hello", session_id="s5"):
            chunks.append(c)
        assert "chunk1" in chunks

    @pytest.mark.asyncio
    async def test_chat_stream_tool_then_final(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        call_count = {"n": 0}

        async def fake_stream(messages, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                yield '{"tool": "calculate_dcf", "args": {}}'
            else:
                yield "final streamed answer"

        mlx.chat_stream = fake_stream
        registry = MagicMock()
        registry.execute = AsyncMock(return_value={"ev": 1000})
        registry.format_prompt.return_value = ""
        engine = CopilotEngine(mlx=mlx, registry=registry)
        chunks = []
        async for c in engine.chat_stream("value X", session_id="s6"):
            chunks.append(c)
        assert "final streamed answer" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_chat_final_strips_tool_json(self):
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(
            side_effect=[
                '{"tool": "calculate_dcf", "args": {}}',
                "non-tool mid",
                'Final with {"tool": "sneak", "args": {}} embedded',
            ]
        )
        registry = MagicMock()
        registry.execute = AsyncMock(return_value={"ev": 1})
        registry.format_prompt.return_value = ""
        engine = CopilotEngine(mlx=mlx, registry=registry)
        result = await engine.chat("go", session_id="s7")
        assert "tool" not in result["reply"] or "[removed]" in result["reply"]

    @pytest.mark.asyncio
    async def test_chat_wall_clock_budget_timeout(self, monkeypatch):
        from fusion_finance.copilot import engine as eng_mod
        from fusion_finance.copilot.engine import CopilotEngine

        mlx = MagicMock()
        mlx.chat = AsyncMock(return_value='{"tool": "calculate_dcf", "args": {}}')
        registry = MagicMock()
        registry.execute = AsyncMock(return_value={"ev": 1})
        registry.format_prompt.return_value = ""
        engine = CopilotEngine(mlx=mlx, registry=registry)
        ticks = {"n": 0}

        def fake_monotonic():
            ticks["n"] += 1
            return 0.0 if ticks["n"] <= 2 else 1000.0

        monkeypatch.setattr(eng_mod.time, "monotonic", fake_monotonic)
        result = await engine.chat("go", session_id="s8")
        assert "时间预算" in result["reply"]
        assert result["tool_calls"]

    @pytest.mark.asyncio
    async def test_extract_tool_calls_variants(self):
        from fusion_finance.copilot.engine import CopilotEngine

        assert CopilotEngine._extract_tool_calls(None) == []
        assert CopilotEngine._extract_tool_calls("str") == []
        assert CopilotEngine._extract_tool_calls({}) == []
        assert CopilotEngine._extract_tool_calls({"tool": "foo", "args": {"x": 1}}) == [("foo", {"x": 1})]
        batch = {"tool_calls": [{"tool": "a", "args": {}}, {"tool": "b"}]}
        result = CopilotEngine._extract_tool_calls(batch)
        assert result == [("a", {}), ("b", {})]

    def test_sanitize_observation(self):
        from fusion_finance.copilot.engine import MAX_TOOL_RESULT_CHARS, _sanitize_observation

        text = 'noise {"tool": "x"} more'
        out = _sanitize_observation(text)
        assert '{"tool"' not in out
        long = "a" * (MAX_TOOL_RESULT_CHARS + 100)
        assert len(_sanitize_observation(long)) <= MAX_TOOL_RESULT_CHARS
        assert _sanitize_observation(123) == "123"

    def test_truncate_messages(self):
        from fusion_finance.copilot.engine import _truncate_messages

        assert _truncate_messages([]) == []
        msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u1"}]
        assert _truncate_messages(msgs) == msgs
        big = [{"role": "system", "content": "s"}, {"role": "user", "content": "x" * 40000}]
        out = _truncate_messages(big, byte_budget=1000)
        assert out[0]["role"] == "system"
        big_no_sys = [{"role": "user", "content": "x" * 40000}]
        out2 = _truncate_messages(big_no_sys, byte_budget=1000)
        assert len(out2) >= 1


class TestCopilotRoutes:
    def _override_engine(self, engine):
        from fusion_finance.api.dependencies import get_copilot_engine, get_mlx_client

        shared_mlx = engine.mlx
        app.dependency_overrides[get_copilot_engine] = lambda: engine
        app.dependency_overrides[get_mlx_client] = lambda: shared_mlx

    def test_chat_route_mock(self):
        engine = MagicMock()
        engine.chat = AsyncMock(
            return_value={"reply": "hi", "tool_calls": [], "rounds": 0, "session_id": "s1"}
        )
        engine.mlx = MagicMock()
        self._override_engine(engine)
        try:
            c = _client()
            resp = c.post("/api/v1/copilot/chat", json={"message": "hello", "session_id": "s1"})
            assert resp.status_code == 200
            assert resp.json()["reply"] == "hi"
        finally:
            app.dependency_overrides.clear()

    def test_history_route(self):
        engine = MagicMock()
        engine.get_history = MagicMock(return_value=[{"role": "user", "content": "hi"}])
        engine.mlx = MagicMock()
        self._override_engine(engine)
        try:
            c = _client()
            resp = c.get("/api/v1/copilot/history/s1")
            assert resp.status_code == 200
            assert "messages" in resp.json()
        finally:
            app.dependency_overrides.clear()

    def test_sessions_route(self):
        engine = MagicMock()
        engine.memory = MagicMock()
        engine.memory.list_sessions = MagicMock(return_value=["s1", "s2"])
        engine.mlx = MagicMock()
        self._override_engine(engine)
        try:
            c = _client()
            resp = c.get("/api/v1/copilot/sessions")
            assert resp.status_code == 200
            assert resp.json()["total"] == 2
        finally:
            app.dependency_overrides.clear()
