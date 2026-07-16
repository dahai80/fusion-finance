"""Coverage tests for Fusion-Finance."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_finance.ai_client import MLXClient
from fusion_finance.modeling import FinancialModelingEngine, DCFModel, CompsAnalysis, AdvancedModelingEngine, LBOModel, DDMModel, MergerModel, APVModel, EVAModel, RIModel, PortfolioOptimizer, Bond, TechnicalIndicators
from fusion_finance.risk import RiskComplianceEngine, KYCCheck, CreditAssessment, RiskModelingEngine, VaRResult, StressTestResult
from fusion_finance.statements import StatementAnalyzer, FinancialStatement, FinancialAnalysis
from fusion_finance.report import ReportGenerator
from fusion_finance.utils import AuditTrail, AuditEntry


class MockMLX:
    chat = AsyncMock(return_value='{"test": "ok"}')


class TestMLXClient:
    @pytest.mark.asyncio
    async def test_chat_auto_discover(self):
        client = MLXClient(base_url="http://localhost:11434/v1")
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=MagicMock(json=lambda: {"data": [{"id": "qwen"}]}))
        mock_http.post = AsyncMock(return_value=MagicMock(
            status_code=200, json=lambda: {"choices": [{"message": {"content": "ok"}}]}
        ))
        client._client = mock_http
        result = await client.chat([{"role": "user", "content": "hi"}])
        assert client.model == "qwen"


class TestModelingEngine:
    @pytest.mark.asyncio
    async def test_build_dcf(self):
        engine = FinancialModelingEngine(mlx=MockMLX())
        result = await engine.build_dcf("Test Corp", [1000, 1100, 1200])
        assert isinstance(result, DCFModel) or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_build_comps(self):
        engine = FinancialModelingEngine(mlx=MockMLX())
        result = await engine.build_comps("Test Corp", [])
        assert isinstance(result, dict) or result is not None


class TestRiskEngine:
    @pytest.mark.asyncio
    async def test_kyc_screening(self):
        engine = RiskComplianceEngine(mlx=MockMLX())
        result = await engine.kyc_screening("Test Corp")
        assert isinstance(result, KYCCheck)

    @pytest.mark.asyncio
    async def test_credit_assessment(self):
        engine = RiskComplianceEngine(mlx=MockMLX())
        result = await engine.credit_assessment("Test Corp", {"revenue": 1000})
        assert isinstance(result, CreditAssessment)

    @pytest.mark.asyncio
    async def test_compliance_check(self):
        engine = RiskComplianceEngine(mlx=MockMLX())
        result = await engine.compliance_check("contract text")
        assert isinstance(result, dict)


class TestReport:
    def test_valuation_report(self):
        r = ReportGenerator()
        dcf = DCFModel(company="Test", enterprise_value=1000, equity_value=800, target_price=50)
        result = r.generate_valuation_report("Test Corp", dcf)
        assert isinstance(result, str)

    def test_save_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            r = ReportGenerator()
            path = r.save_report("content", tmpdir, "test.md")
            assert path.endswith(".md")

class TestAPV:
    def test_apv_calculation(self):
        model = APVModel(company="T", unlevered_fcf=[100, 120, 140], unlevered_cost=0.10, debt=200, tax_rate=0.25)
        result = model.calculate()
        assert result["enterprise_value"] > 0
        assert result["tax_shield"] == 50.0

    def test_apv_no_fcf(self):
        model = APVModel(company="T")
        result = model.calculate()
        assert "error" in result


class TestEVA:
    def test_eva_calculation(self):
        model = EVAModel(company="T", nopat=[100, 120, 140], invested_capital=[1000, 1100, 1200], wacc=0.10)
        result = model.calculate()
        assert len(result["eva_values"]) == 3
        assert result["total_eva"] > 0

    def test_eva_no_data(self):
        model = EVAModel(company="T")
        result = model.calculate()
        assert "error" in result


class TestRI:
    def test_ri_calculation(self):
        model = RIModel(company="T", book_value=500, net_income=[100, 120, 140], cost_of_equity=0.12)
        result = model.calculate()
        assert result["fair_value"] > 500

    def test_ri_no_income(self):
        model = RIModel(company="T")
        result = model.calculate()
        assert "error" in result


class TestPortfolio:
    def test_efficient_frontier(self):
        results = PortfolioOptimizer.efficient_frontier([0.10, 0.12], [0.15, 0.20], [[1, 0.5], [0.5, 1]], num=100)
        assert len(results) > 0

    def test_max_sharpe(self):
        results = [{"sharpe": 0.5, "return": 0.1}, {"sharpe": 1.0, "return": 0.12}]
        best = PortfolioOptimizer.max_sharpe(results)
        assert best["sharpe"] == 1.0

    def test_min_volatility(self):
        results = [{"volatility": 0.15}, {"volatility": 0.10}]
        best = PortfolioOptimizer.min_volatility(results)
        assert best["volatility"] == 0.10

    def test_empty_portfolio(self):
        assert PortfolioOptimizer.efficient_frontier([0.10], [0.15], [[1]]) == []


class TestBond:
    def test_bond_calculation(self):
        bond = Bond(face_value=100, coupon_rate=0.05, years_to_maturity=10, yield_to_maturity=0.06)
        result = bond.calculate()
        assert result["price"] < 100  # 票面利率 < 到期收益率
        assert result["duration"] > 0

    def test_bond_premium(self):
        bond = Bond(face_value=100, coupon_rate=0.08, years_to_maturity=5, yield_to_maturity=0.05)
        result = bond.calculate()
        assert result["price"] > 100


class TestTechnicalIndicators:
    def test_sma(self):
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        sma = TechnicalIndicators.sma(prices, period=5)
        assert len(sma) == 6

    def test_ema(self):
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        ema = TechnicalIndicators.ema(prices, period=5)
        assert len(ema) == 6

    def test_rsi(self):
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        rsi = TechnicalIndicators.rsi(prices, period=5)
        assert len(rsi) > 0

    def test_macd(self):
        prices = [10 + i * 0.5 for i in range(50)]
        macd = TechnicalIndicators.macd(prices)
        assert len(macd) > 0

    def test_sma_short_data(self):
        assert TechnicalIndicators.sma([1, 2, 3], period=5) == []

    def test_rsi_short_data(self):
        assert TechnicalIndicators.rsi([1, 2], period=14) == []
