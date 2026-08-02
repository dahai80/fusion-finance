from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any

from .csv_loader import CSVLoader

logger = logging.getLogger(__name__)


@dataclass
class MarketQuote:
    symbol: str = ""
    name: str = ""
    market: str = ""
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    change_pct: float = 0.0
    timestamp: float = 0.0


@dataclass
class OHLCVBar:
    timestamp: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0


class MarketFeedSimulator:
    A_STOCKS = [
        ("600519", "贵州茅台"),
        ("000858", "五粮液"),
        ("601318", "中国平安"),
        ("600036", "招商银行"),
        ("000333", "美的集团"),
        ("600276", "恒瑞医药"),
        ("601012", "隆基绿能"),
        ("000651", "格力电器"),
        ("600900", "长江电力"),
        ("601888", "中国中免"),
    ]
    HK_STOCKS = [
        ("00700", "腾讯控股"),
        ("09988", "阿里巴巴"),
        ("03690", "美团"),
        ("09618", "京东集团"),
        ("02318", "中国平安H"),
        ("00005", "汇丰控股"),
        ("00941", "中国移动"),
        ("01299", "AIA"),
        ("01810", "小米集团"),
        ("09888", "百度集团"),
    ]

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self._price_state: dict[str, float] = {}
        logger.info("MarketFeedSimulator initialized")

    def generate_quotes(self, market: str = "A") -> list[MarketQuote]:
        stocks = self.A_STOCKS if market.upper() == "A" else self.HK_STOCKS
        quotes = []
        now = time.time()
        for symbol, name in stocks:
            base = self._price_state.get(symbol, random.uniform(10, 2000))
            change_pct = random.gauss(0, 0.03)
            close = round(base * (1 + change_pct), 2)
            high = round(close * (1 + abs(random.gauss(0, 0.01))), 2)
            low = round(close * (1 - abs(random.gauss(0, 0.01))), 2)
            open_price = round(random.uniform(low, high), 2)
            volume = random.randint(100000, 50000000)
            self._price_state[symbol] = close
            quotes.append(
                MarketQuote(
                    symbol=symbol,
                    name=name,
                    market=market,
                    open_price=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    change_pct=round(change_pct * 100, 2),
                    timestamp=now,
                )
            )
        logger.info("Generated %d quotes for market %s", len(quotes), market)
        return quotes

    def generate_ohlcv_series(self, symbol: str, base_price: float = 100.0, bars: int = 60) -> list[OHLCVBar]:
        series = []
        price = base_price
        now = time.time()
        day_seconds = 86400
        for i in range(bars):
            change = random.gauss(0, 0.02)
            price = price * (1 + change)
            high = price * (1 + abs(random.gauss(0, 0.005)))
            low = price * (1 - abs(random.gauss(0, 0.005)))
            open_price = random.uniform(low, high)
            volume = random.randint(1000000, 20000000)
            series.append(
                OHLCVBar(
                    timestamp=now - (bars - i) * day_seconds,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(price, 2),
                    volume=volume,
                )
            )
        logger.info("Generated %d OHLCV bars for %s", bars, symbol)
        return series


class MarketDataAdapter:
    def __init__(self):
        self._simulator = MarketFeedSimulator()
        self._csv_loader = CSVLoader()
        logger.info("MarketDataAdapter initialized")

    def get_quotes(self, market: str = "A") -> list[dict[str, Any]]:
        quotes = self._simulator.generate_quotes(market)
        return [
            {
                "symbol": q.symbol,
                "name": q.name,
                "market": q.market,
                "open": q.open_price,
                "high": q.high,
                "low": q.low,
                "close": q.close,
                "volume": q.volume,
                "change_pct": q.change_pct,
                "timestamp": q.timestamp,
            }
            for q in quotes
        ]

    def get_ohlcv(self, symbol: str, base_price: float = 100.0, bars: int = 60) -> list[dict[str, Any]]:
        series = self._simulator.generate_ohlcv_series(symbol, base_price, bars)
        return [
            {
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in series
        ]

    def load_market_csv(self, source: str, symbol_field: str = "symbol", close_field: str = "close") -> dict[str, Any]:
        data = self._csv_loader.load(source)
        if not data:
            return {"symbol": "", "bars": [], "count": 0}
        bars = []
        for row in data:
            try:
                bars.append(
                    {
                        "symbol": str(row.get(symbol_field, "")),
                        "close": float(row.get(close_field, 0)),
                        "open": float(row.get("open", row.get(close_field, 0))),
                        "high": float(row.get("high", row.get(close_field, 0))),
                        "low": float(row.get("low", row.get(close_field, 0))),
                        "volume": int(row.get("volume", 0)) if row.get("volume") else 0,
                    }
                )
            except (ValueError, TypeError):
                continue
        symbol = bars[0]["symbol"] if bars else ""
        logger.info("Loaded market CSV: symbol=%s, bars=%d", symbol, len(bars))
        return {"symbol": symbol, "bars": bars, "count": len(bars)}

    def compute_technicals(self, ohlcv: list[dict[str, Any]]) -> dict[str, Any]:
        from ..modeling.portfolio import TechnicalIndicators

        closes = [b["close"] for b in ohlcv if "close" in b]
        result = {"bar_count": len(closes)}
        if len(closes) >= 20:
            result["sma_20"] = TechnicalIndicators.sma(closes, 20)
        if len(closes) >= 50:
            result["sma_50"] = TechnicalIndicators.sma(closes, 50)
        if len(closes) >= 15:
            result["rsi_14"] = TechnicalIndicators.rsi(closes, 14)
        if len(closes) >= 35:
            result["macd"] = TechnicalIndicators.macd(closes)
        logger.info("Computed technicals for %d bars", len(closes))
        return result
