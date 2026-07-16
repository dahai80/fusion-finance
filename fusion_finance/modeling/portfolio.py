"""投资组合优化 — 有效前沿、马克维茨、固定收益、技术分析。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Portfolio:
    assets: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    volatilities: List[float] = field(default_factory=list)
    portfolio_return: float = 0.0
    portfolio_volatility: float = 0.0
    sharpe_ratio: float = 0.0


class PortfolioOptimizer:
    @staticmethod
    def efficient_frontier(returns, vols, corr, risk_free=0.03, num=1000):
        n = len(returns)
        if n < 2:
            return []
        portfolios = []
        for _ in range(num):
            w = [random.random() for _ in range(n)]
            total = sum(w)
            w = [wi / total for wi in w]
            port_ret = sum(w[i] * returns[i] for i in range(n))
            port_var = sum(w[i] * w[j] * vols[i] * vols[j] * corr[i][j] for i in range(n) for j in range(n))
            port_vol = math.sqrt(port_var) if port_var > 0 else 0
            sharpe = (port_ret - risk_free) / port_vol if port_vol > 0 else 0
            portfolios.append({"return": round(port_ret, 4), "volatility": round(port_vol, 4), "sharpe": round(sharpe, 4), "weights": w})
        return portfolios

    @staticmethod
    def max_sharpe(portfolios):
        return max(portfolios, key=lambda p: p["sharpe"]) if portfolios else {}

    @staticmethod
    def min_volatility(portfolios):
        return min(portfolios, key=lambda p: p["volatility"]) if portfolios else {}


@dataclass
class Bond:
    face_value: float = 100.0
    coupon_rate: float = 0.05
    years_to_maturity: int = 10
    yield_to_maturity: float = 0.06
    payment_freq: int = 2
    price: float = 0.0
    duration: float = 0.0
    convexity: float = 0.0

    def calculate(self):
        c = self.coupon_rate / self.payment_freq
        y = self.yield_to_maturity / self.payment_freq
        n = self.years_to_maturity * self.payment_freq
        coupon = self.face_value * c
        self.price = sum(coupon / (1 + y) ** t for t in range(1, n + 1)) + self.face_value / (1 + y) ** n
        self.duration = sum(t * coupon / (1 + y) ** t for t in range(1, n + 1)) / self.price + n * self.face_value / (1 + y) ** n / self.price
        md = self.duration / (1 + y)
        self.convexity = sum(t * (t + 1) * coupon / (1 + y) ** (t + 2) for t in range(1, n + 1)) / self.price
        return {"price": round(self.price, 2), "duration": round(self.duration, 4),
                "modified_duration": round(md, 4), "convexity": round(self.convexity, 4)}


class TechnicalIndicators:
    @staticmethod
    def sma(prices, period=20):
        if len(prices) < period:
            return []
        return [sum(prices[i - period:i]) / period for i in range(period, len(prices) + 1)]

    @staticmethod
    def ema(prices, period=20):
        if len(prices) < period:
            return []
        k = 2 / (period + 1)
        result = [sum(prices[:period]) / period]
        for p in prices[period:]:
            result.append(p * k + result[-1] * (1 - k))
        return result

    @staticmethod
    def rsi(prices, period=14):
        if len(prices) < period + 1:
            return []
        gains, losses = [], []
        for i in range(1, period + 1):
            diff = prices[i] - prices[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        results = []
        for i in range(period, len(prices)):
            diff = prices[i] - prices[i - 1]
            avg_gain = (avg_gain * (period - 1) + max(diff, 0)) / period
            avg_loss = (avg_loss * (period - 1) + max(-diff, 0)) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            results.append(round(100 - 100 / (1 + rs), 2))
        return results

    @staticmethod
    def macd(prices):
        ema12 = TechnicalIndicators.ema(prices, 12)
        ema26 = TechnicalIndicators.ema(prices, 26)
        if len(ema12) < 9:
            return []
        offset = len(ema12) - len(ema26)
        macd_line = [ema12[i] - ema26[i - offset] for i in range(len(ema12))]
        signal = TechnicalIndicators.ema(macd_line, 9)
        return [{"macd": round(macd_line[i], 4), "signal": round(signal[i], 4) if i < len(signal) else 0,
                 "histogram": round(macd_line[i] - signal[i], 4) if i < len(signal) else 0}
                for i in range(len(macd_line))]
