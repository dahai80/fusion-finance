"""投资组合优化 — 有效前沿、马克维茨、BL模型、固定收益、技术分析。"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Portfolio:
    assets: list[str] = field(default_factory=list)
    weights: list[float] = field(default_factory=list)
    returns: list[float] = field(default_factory=list)
    volatilities: list[float] = field(default_factory=list)
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
            portfolios.append(
                {
                    "return": round(port_ret, 4),
                    "volatility": round(port_vol, 4),
                    "sharpe": round(sharpe, 4),
                    "weights": w,
                }
            )
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
        self.duration = (
            sum(t * coupon / (1 + y) ** t for t in range(1, n + 1)) / self.price
            + n * self.face_value / (1 + y) ** n / self.price
        )
        md = self.duration / (1 + y)
        self.convexity = sum(t * (t + 1) * coupon / (1 + y) ** (t + 2) for t in range(1, n + 1)) / self.price
        return {
            "price": round(self.price, 2),
            "duration": round(self.duration, 4),
            "modified_duration": round(md, 4),
            "convexity": round(self.convexity, 4),
        }


class TechnicalIndicators:
    @staticmethod
    def sma(prices, period=20):
        if len(prices) < period:
            return []
        return [sum(prices[i - period : i]) / period for i in range(period, len(prices) + 1)]

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
        return [
            {
                "macd": round(macd_line[i], 4),
                "signal": round(signal[i], 4) if i < len(signal) else 0,
                "histogram": round(macd_line[i] - signal[i], 4) if i < len(signal) else 0,
            }
            for i in range(len(macd_line))
        ]


class BlackLittermanOptimizer:
    @staticmethod
    def posterior_returns(
        market_weights: list[float],
        cov_matrix: list[list[float]],
        risk_aversion: float = 2.5,
        views: list[list[float]] | None = None,
        view_returns: list[float] | None = None,
        tau: float = 0.05,
    ) -> list[float]:
        n = len(market_weights)
        if n < 2:
            logger.warning("BL posterior: need >=2 assets, got %d", n)
            return []
        pi = [risk_aversion * sum(cov_matrix[i][j] * market_weights[j] for j in range(n)) for i in range(n)]
        if not views or not view_returns:
            logger.debug("BL: no views, returning implied equilibrium returns")
            return [round(r, 6) for r in pi]
        p = views
        q = view_returns
        omega = [
            [
                tau * sum(p[k][i] * sum(cov_matrix[i][j] * p[k][j] for j in range(n)) for i in range(n))
                if k == m
                else 0.0
                for m in range(len(p))
            ]
            for k in range(len(p))
        ]
        cov_inv = BlackLittermanOptimizer._invert_matrix([[cov_matrix[i][j] / tau for j in range(n)] for i in range(n)])
        if not cov_inv:
            logger.warning("BL: covariance matrix not invertible, falling back to equilibrium")
            return [round(r, 6) for r in pi]
        omega_inv = BlackLittermanOptimizer._invert_matrix(omega)
        if not omega_inv:
            omega_inv = [[0.0] * len(p)] * len(p)
        p_t = [[p[j][i] for j in range(len(p))] for i in range(n)]
        tau_cov_inv = cov_inv
        left = BlackLittermanOptimizer._add_matrices(
            tau_cov_inv,
            BlackLittermanOptimizer._mat_mul(BlackLittermanOptimizer._mat_mul(p_t, omega_inv), p),
        )
        left_inv = BlackLittermanOptimizer._invert_matrix(left)
        if not left_inv:
            return [round(r, 6) for r in pi]
        right_part1 = BlackLittermanOptimizer._mat_vec(tau_cov_inv, pi)
        right_part2 = BlackLittermanOptimizer._mat_vec(BlackLittermanOptimizer._mat_mul(p_t, omega_inv), q)
        right = [right_part1[i] + right_part2[i] for i in range(n)]
        mu_bl = BlackLittermanOptimizer._mat_vec(left_inv, right)
        logger.info("BL posterior returns computed for %d assets", n)
        return [round(r, 6) for r in mu_bl]

    @staticmethod
    def optimize(
        posterior_returns: list[float],
        cov_matrix: list[list[float]],
        risk_aversion: float = 2.5,
        risk_free: float = 0.03,
    ) -> dict:
        n = len(posterior_returns)
        if n < 2:
            return {"weights": [], "expected_return": 0.0, "volatility": 0.0, "sharpe": 0.0}
        best_sharpe = -1.0
        best_w = [1.0 / n] * n
        for _ in range(5000):
            w = [random.random() for _ in range(n)]
            total = sum(w)
            w = [wi / total for wi in w]
            ret = sum(w[i] * posterior_returns[i] for i in range(n))
            var = sum(w[i] * w[j] * cov_matrix[i][j] for i in range(n) for j in range(n))
            vol = math.sqrt(var) if var > 0 else 0
            sharpe = (ret - risk_free) / vol if vol > 0 else 0
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_w = w
        ret = sum(best_w[i] * posterior_returns[i] for i in range(n))
        var = sum(best_w[i] * best_w[j] * cov_matrix[i][j] for i in range(n) for j in range(n))
        vol = math.sqrt(var) if var > 0 else 0
        logger.info("BL optimize: sharpe=%.4f, return=%.4f, vol=%.4f", best_sharpe, ret, vol)
        return {
            "weights": [round(w, 4) for w in best_w],
            "expected_return": round(ret, 6),
            "volatility": round(vol, 6),
            "sharpe": round(best_sharpe, 4),
        }

    @staticmethod
    def _invert_matrix(m: list[list[float]]) -> list[list[float]] | None:
        n = len(m)
        if n == 0:
            return None
        aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
        for col in range(n):
            pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
            if abs(aug[pivot][col]) < 1e-12:
                return None
            aug[col], aug[pivot] = aug[pivot], aug[col]
            for row in range(n):
                if row != col:
                    factor = aug[row][col] / aug[col][col]
                    for j in range(2 * n):
                        aug[row][j] -= factor * aug[col][j]
        result = []
        for i in range(n):
            d = aug[i][i]
            if abs(d) < 1e-12:
                return None
            result.append([aug[i][n + j] / d for j in range(n)])
        return result

    @staticmethod
    def _mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
        rows, cols, inner = len(a), len(b[0]) if b else 0, len(b)
        return [[sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)] for i in range(rows)]

    @staticmethod
    def _add_matrices(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    @staticmethod
    def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
        return [sum(m[i][j] * v[j] for j in range(len(v))) for i in range(len(m))]


@dataclass
class YieldCurve:
    tau1: float = 0.0609
    tau2: float = 0.0404
    beta0: float = 0.04
    beta1: float = -0.02
    beta2: float = -0.01
    beta3: float = 0.0

    def nelson_siegel(self, maturities: list[float]) -> list[float]:
        rates = []
        for t in maturities:
            if t <= 0:
                rates.append(self.beta0 + self.beta1)
                continue
            f1 = (1 - math.exp(-t / self.tau1)) / (t / self.tau1)
            f2 = f1 - math.exp(-t / self.tau1)
            f3 = (1 - math.exp(-t / self.tau2)) / (t / self.tau2) - math.exp(-t / self.tau2)
            rate = self.beta0 + self.beta1 * f1 + self.beta2 * f2 + self.beta3 * f3
            rates.append(round(rate, 6))
        logger.info("NS yield curve: %d maturities", len(maturities))
        return rates

    def calibrate(self, observed_maturities: list[float], observed_rates: list[float]) -> dict:
        if len(observed_maturities) < 4 or len(observed_rates) != len(observed_maturities):
            logger.warning("NS calibrate: need >=4 observations, got %d", len(observed_maturities))
            return {"beta0": self.beta0, "beta1": self.beta1, "beta2": self.beta2, "beta3": self.beta3}
        best_err = float("inf")
        best = (self.beta0, self.beta1, self.beta2, self.beta3)
        for _ in range(2000):
            b0 = random.uniform(0.0, 0.10)
            b1 = random.uniform(-0.10, 0.10)
            b2 = random.uniform(-0.10, 0.10)
            b3 = random.uniform(-0.05, 0.05)
            t1 = random.uniform(0.01, 0.5)
            t2 = random.uniform(0.01, 0.5)
            err = 0.0
            for i, t in enumerate(observed_maturities):
                if t <= 0:
                    pred = b0 + b1
                else:
                    f1 = (1 - math.exp(-t / t1)) / (t / t1)
                    f2 = f1 - math.exp(-t / t1)
                    f3 = (1 - math.exp(-t / t2)) / (t / t2) - math.exp(-t / t2)
                    pred = b0 + b1 * f1 + b2 * f2 + b3 * f3
                err += (pred - observed_rates[i]) ** 2
            if err < best_err:
                best_err = err
                best = (b0, b1, b2, b3, t1, t2)
        self.beta0, self.beta1, self.beta2, self.beta3 = best[0], best[1], best[2], best[3]
        self.tau1, self.tau2 = best[4], best[5]
        logger.info("NS calibrated: betas=%.4f,%.4f,%.4f,%.4f tau=%.4f,%.4f err=%.6f", *best, best_err)
        return {
            "beta0": round(self.beta0, 6),
            "beta1": round(self.beta1, 6),
            "beta2": round(self.beta2, 6),
            "beta3": round(self.beta3, 6),
            "tau1": round(self.tau1, 6),
            "tau2": round(self.tau2, 6),
            "mse": round(best_err / len(observed_maturities), 8),
        }

    def interpolate(self, target_maturity: float) -> float:
        rates = self.nelson_siegel([target_maturity])
        return rates[0] if rates else 0.0
