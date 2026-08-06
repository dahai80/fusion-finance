from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScreenFilter:
    metric: str = ""
    min_val: float | None = None
    max_val: float | None = None


@dataclass
class StockEntry:
    ticker: str = ""
    name: str = ""
    sector: str = ""
    market: str = "A"
    metrics: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    rank: int = 0


VALUE_PRESET = [
    ScreenFilter(metric="pe_ratio", max_val=20.0),
    ScreenFilter(metric="pb_ratio", max_val=3.5),
    ScreenFilter(metric="dividend_yield", min_val=2.5),
    ScreenFilter(metric="debt_ratio", max_val=65.0),
]

GROWTH_PRESET = [
    ScreenFilter(metric="revenue_growth", min_val=15.0),
    ScreenFilter(metric="net_margin", min_val=10.0),
    ScreenFilter(metric="roe", min_val=15.0),
]

DIVIDEND_PRESET = [
    ScreenFilter(metric="dividend_yield", min_val=3.5),
    ScreenFilter(metric="payout_ratio", max_val=80.0),
    ScreenFilter(metric="debt_ratio", max_val=70.0),
]

QUALITY_PRESET = [
    ScreenFilter(metric="roe", min_val=15.0),
    ScreenFilter(metric="net_margin", min_val=12.0),
    ScreenFilter(metric="debt_ratio", max_val=40.0),
    ScreenFilter(metric="revenue_growth", min_val=5.0),
]

PRESETS: dict[str, list[ScreenFilter]] = {
    "value": VALUE_PRESET,
    "growth": GROWTH_PRESET,
    "dividend": DIVIDEND_PRESET,
    "quality": QUALITY_PRESET,
}

SCORING_WEIGHTS: dict[str, float] = {
    "roe": 0.20,
    "net_margin": 0.15,
    "revenue_growth": 0.15,
    "debt_ratio": -0.10,
    "pe_ratio": -0.10,
    "pb_ratio": -0.05,
    "dividend_yield": 0.15,
    "current_ratio": 0.10,
}


class FinancialScreener:
    def __init__(self, stocks: list[StockEntry] | None = None):
        self.stocks: list[StockEntry] = stocks or []
        self._sample_stocks: list[StockEntry] | None = None

    def add_stock(self, entry: StockEntry) -> None:
        self.stocks.append(entry)
        logger.debug("Added stock: %s (%s)", entry.ticker, entry.name)

    def load_sample_data(self) -> list[StockEntry]:
        if self._sample_stocks is not None:
            self.stocks = list(self._sample_stocks)
            return self.stocks
        samples = [
            StockEntry(
                ticker="600519",
                name="贵州茅台",
                sector="消费",
                market="A",
                metrics={
                    "roe": 31.2,
                    "net_margin": 52.3,
                    "revenue_growth": 16.5,
                    "debt_ratio": 25.8,
                    "pe_ratio": 35.0,
                    "pb_ratio": 10.2,
                    "dividend_yield": 1.5,
                    "current_ratio": 3.2,
                    "payout_ratio": 52.0,
                },
            ),
            StockEntry(
                ticker="601318",
                name="中国平安",
                sector="金融",
                market="A",
                metrics={
                    "roe": 16.8,
                    "net_margin": 15.2,
                    "revenue_growth": 8.3,
                    "debt_ratio": 68.5,
                    "pe_ratio": 8.5,
                    "pb_ratio": 1.1,
                    "dividend_yield": 4.2,
                    "current_ratio": 1.1,
                    "payout_ratio": 35.0,
                },
            ),
            StockEntry(
                ticker="000858",
                name="五粮液",
                sector="消费",
                market="A",
                metrics={
                    "roe": 25.5,
                    "net_margin": 37.8,
                    "revenue_growth": 12.3,
                    "debt_ratio": 22.1,
                    "pe_ratio": 25.0,
                    "pb_ratio": 7.5,
                    "dividend_yield": 2.1,
                    "current_ratio": 2.8,
                    "payout_ratio": 55.0,
                },
            ),
            StockEntry(
                ticker="600036",
                name="招商银行",
                sector="金融",
                market="A",
                metrics={
                    "roe": 17.2,
                    "net_margin": 38.5,
                    "revenue_growth": 6.1,
                    "debt_ratio": 91.2,
                    "pe_ratio": 6.0,
                    "pb_ratio": 0.9,
                    "dividend_yield": 5.5,
                    "current_ratio": 1.0,
                    "payout_ratio": 33.0,
                },
            ),
            StockEntry(
                ticker="000333",
                name="美的集团",
                sector="制造",
                market="A",
                metrics={
                    "roe": 24.1,
                    "net_margin": 11.5,
                    "revenue_growth": 9.8,
                    "debt_ratio": 58.3,
                    "pe_ratio": 12.0,
                    "pb_ratio": 3.2,
                    "dividend_yield": 3.8,
                    "current_ratio": 1.3,
                    "payout_ratio": 45.0,
                },
            ),
            StockEntry(
                ticker="00700",
                name="腾讯控股",
                sector="科技",
                market="HK",
                metrics={
                    "roe": 22.5,
                    "net_margin": 29.3,
                    "revenue_growth": 18.7,
                    "debt_ratio": 35.6,
                    "pe_ratio": 22.0,
                    "pb_ratio": 5.1,
                    "dividend_yield": 0.8,
                    "current_ratio": 1.8,
                    "payout_ratio": 20.0,
                },
            ),
            StockEntry(
                ticker="AAPL",
                name="Apple Inc.",
                sector="科技",
                market="US",
                metrics={
                    "roe": 147.0,
                    "net_margin": 25.3,
                    "revenue_growth": 5.2,
                    "debt_ratio": 85.3,
                    "pe_ratio": 30.0,
                    "pb_ratio": 45.0,
                    "dividend_yield": 0.6,
                    "current_ratio": 0.9,
                    "payout_ratio": 16.0,
                },
            ),
            StockEntry(
                ticker="601398",
                name="工商银行",
                sector="金融",
                market="A",
                metrics={
                    "roe": 11.8,
                    "net_margin": 33.2,
                    "revenue_growth": 3.5,
                    "debt_ratio": 91.8,
                    "pe_ratio": 5.0,
                    "pb_ratio": 0.5,
                    "dividend_yield": 6.2,
                    "current_ratio": 1.0,
                    "payout_ratio": 30.0,
                },
            ),
        ]
        self._sample_stocks = list(samples)
        self.stocks = list(samples)
        logger.info("Loaded %d sample stocks", len(samples))
        return self.stocks

    def screen(self, filters: list[ScreenFilter] | None = None, preset: str = "") -> list[StockEntry]:
        if preset and preset in PRESETS:
            filters = PRESETS[preset]
            logger.info("Using preset: %s (%d filters)", preset, len(filters))
        if not filters:
            logger.warning("No filters provided, returning all stocks")
            return list(self.stocks)

        results: list[StockEntry] = []
        for stock in self.stocks:
            passed = True
            for f in filters:
                val = stock.metrics.get(f.metric)
                if val is None:
                    passed = False
                    break
                if f.min_val is not None and val < f.min_val:
                    passed = False
                    break
                if f.max_val is not None and val > f.max_val:
                    passed = False
                    break
            if passed:
                results.append(stock)

        logger.info("Screened %d/%d stocks passed", len(results), len(self.stocks))
        return results

    def score(
        self, stocks: list[StockEntry] | None = None, weights: dict[str, float] | None = None
    ) -> list[StockEntry]:
        targets = stocks if stocks is not None else self.stocks
        w = weights or SCORING_WEIGHTS
        scored: list[StockEntry] = []
        for stock in targets:
            total = 0.0
            for metric, weight in w.items():
                val = stock.metrics.get(metric, 0.0)
                total += val * weight
            entry = StockEntry(
                ticker=stock.ticker,
                name=stock.name,
                sector=stock.sector,
                market=stock.market,
                metrics=dict(stock.metrics),
                score=round(total, 2),
            )
            scored.append(entry)

        scored.sort(key=lambda s: s.score, reverse=True)
        for i, s in enumerate(scored):
            s.rank = i + 1
        logger.info(
            "Scored %d stocks, top: %s (%.2f)",
            len(scored),
            scored[0].ticker if scored else "N/A",
            scored[0].score if scored else 0,
        )
        return scored

    def screen_and_rank(
        self,
        filters: list[ScreenFilter] | None = None,
        preset: str = "",
        weights: dict[str, float] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        filtered = self.screen(filters=filters, preset=preset)
        ranked = self.score(stocks=filtered, weights=weights)
        top = ranked[:limit]
        return {
            "preset": preset or "custom",
            "total_candidates": len(self.stocks),
            "passed_filter": len(filtered),
            "results": [
                {
                    "rank": s.rank,
                    "ticker": s.ticker,
                    "name": s.name,
                    "sector": s.sector,
                    "market": s.market,
                    "score": s.score,
                    "metrics": s.metrics,
                }
                for s in top
            ],
        }

    @staticmethod
    def list_presets() -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for name, filters in PRESETS.items():
            result[name] = [{"metric": f.metric, "min": f.min_val, "max": f.max_val} for f in filters]
        return result
