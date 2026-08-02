"""Phase 2 module tests: copilot, chart, data, websocket."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from fusion_finance.chart import ChartRenderer
from fusion_finance.copilot import ConversationMemory, CopilotEngine, ToolRegistry
from fusion_finance.copilot.memory import ConversationMemory as Memory
from fusion_finance.data import CSVLoader, DataAdapter, DataCache, DataValidator


class TestChartRenderer:
    def test_heatmap(self):
        r = ChartRenderer()
        svg = r.heatmap([[1, 2], [3, 4]], ["A", "B"], ["X", "Y"])
        assert "<svg" in svg
        assert "Sensitivity Matrix" in svg

    def test_heatmap_empty(self):
        r = ChartRenderer()
        svg = r.heatmap([], [], [])
        assert "<svg" in svg

    def test_candlestick(self):
        r = ChartRenderer()
        svg = r.candlestick([{"open": 100, "high": 110, "low": 95, "close": 105}])
        assert "<svg" in svg

    def test_candlestick_empty(self):
        r = ChartRenderer()
        svg = r.candlestick([])
        assert "<svg" in svg

    def test_waterfall(self):
        r = ChartRenderer()
        svg = r.waterfall(["Rev", "Cost", "Profit"], [100, -40, 60])
        assert "<svg" in svg

    def test_waterfall_empty(self):
        r = ChartRenderer()
        svg = r.waterfall([], [])
        assert "<svg" in svg

    def test_sensitivity_tornado(self):
        r = ChartRenderer()
        svg = r.sensitivity_tornado(100, {"wacc": [80, 120], "growth": [70, 130]})
        assert "<svg" in svg

    def test_sensitivity_tornado_empty(self):
        r = ChartRenderer()
        svg = r.sensitivity_tornado(0, {})
        assert "<svg" in svg


class TestCSVLoader:
    def test_load_from_string(self):
        loader = CSVLoader()
        data = loader.load("name,revenue,net_income\nApple,100,20\nGoogle,200,30")
        assert len(data) == 2
        assert data[0]["name"] == "Apple"
        assert data[0]["revenue"] == 100

    def test_no_header(self):
        loader = CSVLoader()
        data = loader.load("Apple,100\nGoogle,200", has_header=False)
        assert len(data) == 2
        assert "col_0" in data[0]

    def test_empty_string(self):
        loader = CSVLoader()
        data = loader.load("")
        assert data == []

    def test_auto_type(self):
        loader = CSVLoader()
        data = loader.load("val\n42\n3.14\nhello")
        assert data[0]["val"] == 42
        assert data[1]["val"] == 3.14
        assert data[2]["val"] == "hello"


class TestDataCache:
    def test_set_get(self):
        cache = DataCache()
        cache.set("k1", {"a": 1})
        assert cache.get("k1") == {"a": 1}

    def test_miss(self):
        cache = DataCache()
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = DataCache()
        cache.set("k1", 1)
        assert cache.invalidate("k1") is True
        assert cache.get("k1") is None

    def test_clear(self):
        cache = DataCache()
        cache.set("k1", 1)
        cache.set("k2", 2)
        cache.clear()
        assert cache.size() == 0

    def test_make_key(self):
        k1 = DataCache.make_key("csv", "test.csv")
        k2 = DataCache.make_key("csv", "test.csv")
        k3 = DataCache.make_key("csv", "other.csv")
        assert k1 == k2
        assert k1 != k3


class TestDataValidator:
    def test_validate_row_ok(self):
        v = DataValidator()
        ok, errors = v.validate_row({"revenue": 100}, required_fields=["revenue"])
        assert ok

    def test_validate_row_missing(self):
        v = DataValidator()
        ok, errors = v.validate_row({}, required_fields=["revenue"])
        assert not ok

    def test_validate_balance_sheet(self):
        v = DataValidator()
        ok, _ = v.validate_balance_sheet(100, 40, 60)
        assert ok

    def test_validate_balance_sheet_fail(self):
        v = DataValidator()
        ok, _ = v.validate_balance_sheet(100, 30, 60)
        assert not ok

    def test_sanitize_numeric(self):
        v = DataValidator()
        assert abs(v.sanitize_numeric("$1,234.56") - 1234.56) < 0.01
        assert v.sanitize_numeric(None) == 0.0

    def test_check_completeness(self):
        v = DataValidator()
        data = [{"revenue": 100}, {"revenue": None}]
        scores = v.check_completeness(data, ["revenue"])
        assert scores["revenue"] == 0.5


class TestDataAdapter:
    def test_load_csv(self):
        adapter = DataAdapter()
        result = adapter.load_csv("name,value\nA,10\nB,20")
        assert result["row_count"] == 2
        assert result["valid_rows"] == 2

    def test_validate_balance(self):
        adapter = DataAdapter()
        result = adapter.validate_balance(100, 40, 60)
        assert result["balanced"]

    def test_check_completeness(self):
        adapter = DataAdapter()
        result = adapter.check_completeness([{"revenue": 100}], ["revenue"])
        assert result["overall_score"] == 1.0


class TestConversationMemory:
    def test_add_get_messages(self):
        mem = ConversationMemory()
        sid = "test-session"
        mem.add_message(sid, "user", "hello")
        mem.add_message(sid, "assistant", "hi")
        msgs = mem.get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"

    def test_session_id_generation(self):
        sid = Memory.new_session_id()
        assert len(sid) == 12

    def test_list_sessions(self):
        mem = ConversationMemory()
        mem.add_message("s1", "user", "hi")
        mem.add_message("s2", "user", "hello")
        sessions = mem.list_sessions()
        assert len(sessions) == 2

    def test_clear_session(self):
        mem = ConversationMemory()
        mem.add_message("s1", "user", "hi")
        assert mem.clear_session("s1") is True
        assert mem.get_messages("s1") == []


class TestToolRegistry:
    def test_get_definitions(self):
        registry = ToolRegistry()
        defs = registry.get_definitions()
        assert len(defs) > 0

    def test_format_prompt(self):
        registry = ToolRegistry()
        prompt = registry.format_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestCopilotEngine:
    @pytest.mark.asyncio
    async def test_chat_no_tools(self):
        mock_mlx = MagicMock()
        mock_mlx.chat = AsyncMock(return_value="This is a direct answer.")
        engine = CopilotEngine(mock_mlx)
        result = await engine.chat("hello")
        assert "reply" in result
        assert result["rounds"] == 0

    @pytest.mark.asyncio
    async def test_get_history(self):
        mock_mlx = MagicMock()
        mock_mlx.chat = AsyncMock(return_value="ok")
        engine = CopilotEngine(mock_mlx)
        engine.memory.add_message("s1", "user", "hello")
        history = engine.get_history("s1")
        assert len(history) == 1


class TestPhase2APIRoutes:
    @pytest.fixture
    def client(self):
        from fusion_finance.api.app import app

        return TestClient(app)

    def test_chart_candlestick(self, client):
        resp = client.post(
            "/api/v1/chart/candlestick",
            json={
                "data": [{"open": 100, "high": 110, "low": 95, "close": 105}],
                "title": "Test",
            },
        )
        assert resp.status_code == 200
        assert "svg" in resp.json()

    def test_chart_heatmap(self, client):
        resp = client.post(
            "/api/v1/chart/heatmap",
            json={
                "matrix": [[1, 2], [3, 4]],
                "row_labels": ["A", "B"],
                "col_labels": ["X", "Y"],
            },
        )
        assert resp.status_code == 200
        assert "svg" in resp.json()

    def test_chart_waterfall(self, client):
        resp = client.post(
            "/api/v1/chart/waterfall",
            json={
                "categories": ["Rev", "Cost", "Profit"],
                "values": [100, -40, 60],
            },
        )
        assert resp.status_code == 200

    def test_chart_sensitivity(self, client):
        resp = client.post(
            "/api/v1/chart/sensitivity",
            json={
                "factors": ["wacc", "growth"],
                "low_values": [80, 70],
                "high_values": [120, 130],
                "base_value": 100,
            },
        )
        assert resp.status_code == 200

    def test_data_validate_balance(self, client):
        resp = client.post(
            "/api/v1/data/validate/balance",
            json={
                "assets": 100,
                "liabilities": 40,
                "equity": 60,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["balanced"] is True

    def test_data_validate_completeness(self, client):
        resp = client.post(
            "/api/v1/data/validate/completeness",
            json={
                "data": [{"revenue": 100}],
                "required_fields": ["revenue"],
            },
        )
        assert resp.status_code == 200

    def test_data_cache_list(self, client):
        resp = client.get("/api/v1/data/cache")
        assert resp.status_code == 200

    def test_copilot_sessions(self, client):
        resp = client.get("/api/v1/copilot/sessions")
        assert resp.status_code == 200
