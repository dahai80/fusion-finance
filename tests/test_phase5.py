from __future__ import annotations

import random

from fusion_finance.data.cache import DataCache, compute_cache
from fusion_finance.data.market_feed import MarketDataAdapter, MarketFeedSimulator
from fusion_finance.modeling.engine import FinancialModelingEngine
from fusion_finance.modeling.portfolio import BlackLittermanOptimizer, YieldCurve
from fusion_finance.risk.entity_resolution import (
    EntityGraph,
    EntityNode,
    EntityRelation,
    EntityResolver,
)
from fusion_finance.risk.sanctions import SanctionsEngine


class TestBlackLitterman:
    def setup_method(self):
        self.weights = [0.4, 0.3, 0.3]
        self.cov = [
            [0.04, 0.006, 0.002],
            [0.006, 0.09, 0.006],
            [0.002, 0.006, 0.01],
        ]

    def test_posterior_no_views(self):
        result = BlackLittermanOptimizer.posterior_returns(self.weights, self.cov)
        assert len(result) == 3
        assert all(isinstance(r, float) for r in result)

    def test_posterior_with_views(self):
        views = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        view_returns = [0.12, 0.08]
        result = BlackLittermanOptimizer.posterior_returns(
            self.weights,
            self.cov,
            views=views,
            view_returns=view_returns,
        )
        assert len(result) == 3

    def test_posterior_single_asset(self):
        result = BlackLittermanOptimizer.posterior_returns([1.0], [[0.04]])
        assert result == []

    def test_optimize(self):
        posterior = [0.10, 0.08, 0.06]
        result = BlackLittermanOptimizer.optimize(posterior, self.cov)
        assert "weights" in result
        assert "expected_return" in result
        assert "volatility" in result
        assert "sharpe" in result
        assert abs(sum(result["weights"]) - 1.0) < 0.01

    def test_optimize_single_asset(self):
        result = BlackLittermanOptimizer.optimize([0.1], [[0.04]])
        assert result["weights"] == []

    def test_invert_matrix_2x2(self):
        m = [[4, 7], [2, 6]]
        inv = BlackLittermanOptimizer._invert_matrix(m)
        assert inv is not None
        assert abs(inv[0][0] * 4 + inv[0][1] * 2 - 1) < 1e-10

    def test_invert_matrix_singular(self):
        inv = BlackLittermanOptimizer._invert_matrix([[1, 2], [2, 4]])
        assert inv is None

    def test_invert_matrix_empty(self):
        assert BlackLittermanOptimizer._invert_matrix([]) is None


class TestYieldCurve:
    def test_nelson_siegel(self):
        yc = YieldCurve()
        maturities = [0.25, 0.5, 1, 2, 5, 10, 30]
        rates = yc.nelson_siegel(maturities)
        assert len(rates) == 7
        assert all(isinstance(r, float) for r in rates)

    def test_nelson_siegel_zero_maturity(self):
        yc = YieldCurve()
        rates = yc.nelson_siegel([0])
        assert len(rates) == 1

    def test_interpolate(self):
        yc = YieldCurve()
        rate = yc.interpolate(5.0)
        assert isinstance(rate, float)

    def test_calibrate(self):
        random.seed(42)
        yc = YieldCurve()
        maturities = [0.25, 0.5, 1, 2, 5, 10, 20, 30]
        true_yc = YieldCurve(beta0=0.05, beta1=-0.03, beta2=-0.02, beta3=0.01)
        rates = true_yc.nelson_siegel(maturities)
        params = yc.calibrate(maturities, rates)
        assert "beta0" in params
        assert "mse" in params

    def test_calibrate_insufficient_data(self):
        yc = YieldCurve()
        params = yc.calibrate([1, 2], [0.04, 0.05])
        assert "beta0" in params


class TestSanctionsEngine:
    def test_exact_match(self):
        engine = SanctionsEngine()
        matches = engine.screen("Daesh")
        assert len(matches) >= 1
        assert matches[0].match_type == "exact"
        assert matches[0].score == 1.0

    def test_contains_match(self):
        engine = SanctionsEngine()
        matches = engine.screen("Iran")
        assert any(m.match_type == "contains" for m in matches)

    def test_no_match(self):
        engine = SanctionsEngine()
        matches = engine.screen("Apple Inc")
        assert len(matches) == 0

    def test_fuzzy_match(self):
        engine = SanctionsEngine()
        matches = engine.screen("Al Qaida", threshold=0.5)
        assert len(matches) >= 1

    def test_empty_entity(self):
        engine = SanctionsEngine()
        assert engine.screen("") == []
        assert engine.screen("   ") == []

    def test_batch_screen(self):
        engine = SanctionsEngine()
        results = engine.screen_batch(["Daesh", "Apple Inc"])
        assert "Daesh" in results
        assert "Apple Inc" in results
        assert len(results["Daesh"]) >= 1
        assert len(results["Apple Inc"]) == 0

    def test_add_entry(self):
        engine = SanctionsEngine([])
        engine.add_entry({"name": "Test Entity", "country": "XX", "type": "entity", "program": "TEST"})
        matches = engine.screen("Test Entity")
        assert len(matches) == 1

    def test_levenshtein_ratio(self):
        score = SanctionsEngine._levenshtein_ratio("hello", "hello")
        assert score == 1.0
        score = SanctionsEngine._levenshtein_ratio("", "test")
        assert score == 0.0

    def test_keyword_match(self):
        score = SanctionsEngine._keyword_match("bank of russia", "bank russia financial")
        assert score > 0


class TestEntityResolution:
    def _build_sample_graph(self):
        graph = EntityGraph()
        graph.add_node(EntityNode(id="C1", name="公司A", entity_type="company", country="CN"))
        graph.add_node(EntityNode(id="P1", name="张三", entity_type="person", country="CN"))
        graph.add_node(EntityNode(id="P2", name="李四", entity_type="pep", country="CN"))
        graph.add_node(EntityNode(id="C2", name="公司B", entity_type="company", country="HK"))
        graph.add_relation(EntityRelation(source_id="P1", target_id="C1", relation_type="ownership", weight=0.6))
        graph.add_relation(EntityRelation(source_id="P2", target_id="C1", relation_type="ownership", weight=0.4))
        graph.add_relation(EntityRelation(source_id="C2", target_id="C1", relation_type="investment", weight=0.3))
        return graph

    def test_add_node(self):
        graph = self._build_sample_graph()
        assert "C1" in graph.nodes
        assert graph.nodes["C1"].name == "公司A"

    def test_get_children(self):
        graph = self._build_sample_graph()
        children = graph.get_children("P1")
        assert len(children) == 1
        assert children[0].id == "C1"

    def test_get_parents(self):
        graph = self._build_sample_graph()
        parents = graph.get_parents("C1")
        assert len(parents) == 3

    def test_to_dict(self):
        graph = self._build_sample_graph()
        d = graph.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert d["summary"]["node_count"] == 4

    def test_resolve_ubo(self):
        graph = self._build_sample_graph()
        resolver = EntityResolver()
        ubos = resolver.resolve_ubo(graph, "C1")
        assert len(ubos) >= 2
        assert any(u["name"] == "张三" for u in ubos)

    def test_find_pep_connections(self):
        graph = self._build_sample_graph()
        resolver = EntityResolver()
        pep = resolver.find_pep_connections(graph)
        assert len(pep) >= 1
        assert any(p["pep_name"] == "李四" for p in pep)

    def test_build_from_structure(self):
        structure = {
            "nodes": [
                {"id": "N1", "name": "Entity1", "type": "company"},
                {"id": "N2", "name": "Entity2", "type": "person"},
            ],
            "edges": [
                {"source": "N2", "target": "N1", "type": "ownership", "weight": 0.8},
            ],
        }
        resolver = EntityResolver()
        graph = resolver.build_from_structure(structure)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1


class TestMarketFeed:
    def test_generate_a_quotes(self):
        sim = MarketFeedSimulator(seed=42)
        quotes = sim.generate_quotes("A")
        assert len(quotes) == 10
        assert all(q.market == "A" for q in quotes)

    def test_generate_hk_quotes(self):
        sim = MarketFeedSimulator(seed=42)
        quotes = sim.generate_quotes("HK")
        assert len(quotes) == 10
        assert all(q.market == "HK" for q in quotes)

    def test_generate_ohlcv(self):
        sim = MarketFeedSimulator(seed=42)
        series = sim.generate_ohlcv_series("600519", base_price=100.0, bars=30)
        assert len(series) == 30
        assert all(b.close > 0 for b in series)

    def test_adapter_get_quotes(self):
        adapter = MarketDataAdapter()
        quotes = adapter.get_quotes("A")
        assert len(quotes) == 10
        assert "symbol" in quotes[0]

    def test_adapter_get_ohlcv(self):
        adapter = MarketDataAdapter()
        ohlcv = adapter.get_ohlcv("00700", base_price=300.0, bars=20)
        assert len(ohlcv) == 20

    def test_adapter_compute_technicals(self):
        adapter = MarketDataAdapter()
        ohlcv = adapter.get_ohlcv("600519", bars=60)
        techs = adapter.compute_technicals(ohlcv)
        assert "bar_count" in techs
        assert techs["bar_count"] == 60
        assert "sma_20" in techs
        assert "rsi_14" in techs


class TestBatchDCF:
    def test_batch_dcf(self):
        models = [
            {"company": "A", "revenue": [100, 120, 140], "wacc": 0.1},
            {"company": "B", "revenue": [200, 220, 240], "wacc": 0.12},
        ]
        results = FinancialModelingEngine.batch_dcf(models)
        assert len(results) == 2
        assert results[0]["company"] == "A"
        assert results[1]["company"] == "B"

    def test_batch_dcf_empty(self):
        results = FinancialModelingEngine.batch_dcf([])
        assert results == []


class TestComputeCache:
    def test_cache_decorator(self):
        call_count = 0

        @compute_cache(ttl=60)
        def expensive(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        r1 = expensive(1, 2)
        r2 = expensive(1, 2)
        assert r1 == 3
        assert r2 == 3
        assert call_count == 1

    def test_cache_different_args(self):
        call_count = 0

        @compute_cache(ttl=60)
        def add(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        add(1, 2)
        add(3, 4)
        assert call_count == 2

    def test_data_cache_basic(self):
        cache = DataCache(max_size=10, default_ttl=60)
        cache.set("k1", "v1")
        assert cache.get("k1") == "v1"
        assert cache.has("k1")
        cache.invalidate("k1")
        assert cache.get("k1") is None

    def test_data_cache_lru_eviction(self):
        cache = DataCache(max_size=3, default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("d") == 4
