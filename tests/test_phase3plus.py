from __future__ import annotations

import pytest

from fusion_finance.api.middleware import APIKeyMiddleware, RateLimitMiddleware
from fusion_finance.api.sse import EventBus
from fusion_finance.chart.candlestick import render_candlestick
from fusion_finance.chart.heatmap import render_heatmap
from fusion_finance.chart.renderer import ChartRenderer
from fusion_finance.chart.sensitivity import render_sensitivity_tornado
from fusion_finance.chart.waterfall import render_waterfall
from fusion_finance.copilot.prompts import (
    BASE_SYSTEM_PROMPT,
    INSIGHT_PROMPTS,
    SCENARIO_PROMPTS,
    build_system_prompt,
    get_insight_prompt,
    list_insight_types,
    list_scenarios,
)


class TestCopilotPrompts:
    def test_base_system_prompt(self):
        assert "Fusion-Finance" in BASE_SYSTEM_PROMPT
        assert "AI" in BASE_SYSTEM_PROMPT

    def test_scenarios_defined(self):
        assert "modeling" in SCENARIO_PROMPTS
        assert "risk" in SCENARIO_PROMPTS
        assert "report" in SCENARIO_PROMPTS
        assert "statements" in SCENARIO_PROMPTS
        assert "data" in SCENARIO_PROMPTS

    def test_build_system_prompt_base_only(self):
        result = build_system_prompt()
        assert "Fusion-Finance" in result
        assert "WACC" not in result

    def test_build_system_prompt_with_scenario(self):
        result = build_system_prompt(scenario="modeling")
        assert "Fusion-Finance" in result
        assert "WACC" in result
        assert "估值建模" in result

    def test_build_system_prompt_with_tool_prompt(self):
        result = build_system_prompt(tool_prompt="你可以使用以下工具:\n- dcf")
        assert "dcf" in result

    def test_build_system_prompt_unknown_scenario(self):
        result = build_system_prompt(scenario="unknown")
        assert "Fusion-Finance" in result

    def test_insight_prompts(self):
        assert "valuation_alert" in INSIGHT_PROMPTS
        assert "risk_alert" in INSIGHT_PROMPTS
        assert "data_alert" in INSIGHT_PROMPTS

    def test_get_insight_prompt(self):
        result = get_insight_prompt("valuation_alert")
        assert "WACC" in result

    def test_get_insight_prompt_unknown(self):
        assert get_insight_prompt("nonexistent") == ""

    def test_list_scenarios(self):
        scenarios = list_scenarios()
        assert len(scenarios) == 5
        assert "modeling" in scenarios

    def test_list_insight_types(self):
        types = list_insight_types()
        assert len(types) == 3
        assert "valuation_alert" in types


class TestMiddleware:
    def test_rate_limit_init(self):
        mw = RateLimitMiddleware(app=None, max_requests=50, window_seconds=30)
        assert mw.max_requests == 50
        assert mw.window_seconds == 30

    def test_rate_limit_check_pass(self):
        mw = RateLimitMiddleware(app=None, max_requests=5, window_seconds=60)
        assert mw._check("test_key") is True
        assert mw._check("test_key") is True

    def test_rate_limit_check_block(self):
        mw = RateLimitMiddleware(app=None, max_requests=2, window_seconds=60)
        assert mw._check("test_key") is True
        assert mw._check("test_key") is True
        assert mw._check("test_key") is False

    def test_api_key_middleware_no_key(self):
        mw = APIKeyMiddleware(app=None, api_key="")
        assert mw.api_key == ""

    def test_api_key_middleware_with_key(self):
        mw = APIKeyMiddleware(app=None, api_key="secret123")
        assert mw.api_key == "secret123"

    def test_api_key_exempt_paths(self):
        assert "/api/v1/" in APIKeyMiddleware.EXEMPT_PATHS
        assert "/docs" in APIKeyMiddleware.EXEMPT_PATHS


class TestSSEEventBus:
    def test_subscribe(self):
        bus = EventBus()
        q = bus.subscribe("test_channel")
        assert q is not None
        assert len(bus._subscribers["test_channel"]) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        q = bus.subscribe("test_channel")
        bus.unsubscribe("test_channel", q)
        assert len(bus._subscribers["test_channel"]) == 0

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = EventBus()
        q = bus.subscribe("test_channel")
        await bus.publish("test_channel", {"msg": "hello"})
        data = q.get_nowait()
        assert '"hello"' in data

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self):
        bus = EventBus()
        await bus.publish("empty_channel", {"msg": "test"})


class TestChartModules:
    def test_heatmap_module(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        result = render_heatmap(matrix, ["A", "B"], ["X", "Y"])
        assert "<svg" in result
        assert "A" in result

    def test_candlestick_module(self):
        ohlcv = [{"open": 100, "high": 110, "low": 95, "close": 105}]
        result = render_candlestick(ohlcv)
        assert "<svg" in result

    def test_waterfall_module(self):
        result = render_waterfall(["Revenue", "COGS", "GM"], [100, -40, 60])
        assert "<svg" in result
        assert "Revenue" in result

    def test_sensitivity_tornado_module(self):
        result = render_sensitivity_tornado(100.0, {"WACC": [90, 110], "Growth": [95, 105]})
        assert "<svg" in result
        assert "WACC" in result

    def test_heatmap_empty(self):
        result = render_heatmap([], [], [])
        assert "No data" in result

    def test_candlestick_empty(self):
        result = render_candlestick([])
        assert "No data" in result

    def test_waterfall_empty(self):
        result = render_waterfall([], [])
        assert "No data" in result

    def test_sensitivity_tornado_empty(self):
        result = render_sensitivity_tornado(100.0, {})
        assert "No data" in result

    def test_renderer_facade_heatmap(self):
        r = ChartRenderer()
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        result = r.heatmap(matrix, ["A", "B"], ["X", "Y"])
        assert "<svg" in result

    def test_renderer_facade_candlestick(self):
        r = ChartRenderer()
        result = r.candlestick([{"open": 100, "high": 110, "low": 95, "close": 105}])
        assert "<svg" in result

    def test_renderer_facade_waterfall(self):
        r = ChartRenderer()
        result = r.waterfall(["A", "B"], [10, -5])
        assert "<svg" in result

    def test_renderer_facade_tornado(self):
        r = ChartRenderer()
        result = r.sensitivity_tornado(100.0, {"X": [90, 110]})
        assert "<svg" in result
