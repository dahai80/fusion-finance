"""Fusion-Finance 核心测试。"""

from __future__ import annotations

import pytest

from fusion_finance.ai_client import MLXClient
from fusion_finance.modeling import FinancialModelingEngine, DCFModel, CompsAnalysis
from fusion_finance.statements import StatementAnalyzer, FinancialStatement, FinancialAnalysis
from fusion_finance.risk import RiskComplianceEngine, KYCCheck, CreditAssessment
from fusion_finance.report import ReportGenerator


class TestDCFModel:
    def test_dcf_calculation(self):
        model = DCFModel(company="Test", revenue=[100, 120, 140], forecast_years=3,
                         ebit_margin=[0.2, 0.22, 0.25], wacc=0.10, terminal_growth=0.03)
        result = model.calculate()
        assert result["enterprise_value"] > 0
        assert result["pv_fcf"] > 0

    def test_dcf_with_target_price(self):
        model = DCFModel(company="Test", revenue=[100, 120], forecast_years=2,
                         ebit_margin=[0.2, 0.22], net_debt=50, shares_outstanding=10)
        result = model.calculate()
        assert result["target_price"] > 0

    def test_dcf_no_revenue(self):
        model = DCFModel(company="Test")
        result = model.calculate()
        assert "error" in result

    def test_dcf_model_fields(self):
        model = DCFModel(company="ABC", revenue=[200, 240], wacc=0.12)
        assert model.company == "ABC"
        assert model.wacc == 0.12


class TestFinancialModelingEngine:
    @pytest.mark.asyncio
    async def test_build_dcf(self):
        engine = FinancialModelingEngine()
        model = await engine.build_dcf("Test", [100, 120, 140])
        assert model.company == "Test"
        assert len(model.revenue) == 3

    @pytest.mark.asyncio
    async def test_build_comps(self):
        engine = FinancialModelingEngine()
        comps = await engine.build_comps("Test", "科技")
        assert comps.company == "Test"

    @pytest.mark.asyncio
    async def test_sensitivity_analysis(self):
        engine = FinancialModelingEngine()
        model = DCFModel(company="Test", revenue=[100, 120], ebit_margin=[0.2, 0.22])
        result = await engine.sensitivity_analysis(model, [0.08, 0.10], [0.02, 0.03])
        assert "matrix" in result

    @pytest.mark.asyncio
    async def test_monte_carlo(self):
        engine = FinancialModelingEngine()
        model = DCFModel(company="Test", revenue=[100, 120], ebit_margin=[0.2, 0.22])
        result = await engine.monte_carlo(model, simulations=100)
        assert result["simulations"] == 100
        assert result["mean"] > 0


class TestStatementAnalyzer:
    def test_calculate_metrics(self):
        stmt = FinancialStatement(company="ABC", revenue=1000, gross_profit=400,
                                  operating_income=200, net_income=150,
                                  total_assets=2000, total_liabilities=800, equity=1200)
        analyzer = StatementAnalyzer()
        analysis = analyzer.calculate_metrics(stmt)
        assert analysis.gross_margin == 40.0
        assert analysis.net_margin == 15.0
        assert analysis.roe == 12.5
        assert analysis.debt_ratio == 40.0

    def test_calculate_metrics_zero_revenue(self):
        stmt = FinancialStatement(company="ABC")
        analyzer = StatementAnalyzer()
        analysis = analyzer.calculate_metrics(stmt)
        assert analysis.gross_margin == 0

    def test_validate_balance_sheet_ok(self):
        stmt = FinancialStatement(company="ABC", period="2024", total_assets=1000,
                                  total_liabilities=400, equity=600)
        analyzer = StatementAnalyzer()
        issues = analyzer.validate_balance_sheet([stmt])
        assert len(issues) == 0

    def test_validate_balance_sheet_error(self):
        stmt = FinancialStatement(company="ABC", period="2024", total_assets=1000,
                                  total_liabilities=300, equity=300)
        analyzer = StatementAnalyzer()
        issues = analyzer.validate_balance_sheet([stmt])
        assert len(issues) >= 1


class TestRiskComplianceEngine:
    @pytest.mark.asyncio
    async def test_kyc_screening(self):
        engine = RiskComplianceEngine()
        result = await engine.kyc_screening("Test Corp")
        assert result.entity == "Test Corp"

    @pytest.mark.asyncio
    async def test_credit_assessment(self):
        engine = RiskComplianceEngine()
        result = await engine.credit_assessment("Test Corp", {"revenue": 1000, "profit": 100})
        assert result.entity == "Test Corp"

    @pytest.mark.asyncio
    async def test_compliance_check(self):
        engine = RiskComplianceEngine()
        result = await engine.compliance_check("Test contract text")
        assert isinstance(result, dict)


class TestReportGenerator:
    def test_valuation_report(self):
        dcf = DCFModel(company="Test", revenue=[100, 120], ebit_margin=[0.2, 0.22])
        dcf.calculate()
        gen = ReportGenerator()
        report = gen.generate_valuation_report("Test", dcf)
        assert "Test" in report
        assert "DCF" in report

    def test_generate_pitchbook(self):
        dcf = DCFModel(company="Test", revenue=[100, 120])
        dcf.calculate()
        gen = ReportGenerator()
        pb = gen.generate_pitchbook("Test", dcf, "科技")
        assert "Test" in pb
        assert "投资亮点" in pb

    def test_save_report(self, tmp_path):
        gen = ReportGenerator()
        path = gen.save_report("# Test", str(tmp_path))
        assert path.endswith(".md")

    @pytest.mark.asyncio
    async def test_research_report(self):
        gen = ReportGenerator()
        result = await gen.generate_research_report("Test", "科技", {"key": "value"})
        assert isinstance(result, str)


class TestMLXClient:
    def test_init(self):
        client = MLXClient(model="test")
        assert client.model == "test"

    def test_default_model(self):
        client = MLXClient()
        assert client.model == ""


class TestModuleIntegrity:
    def test_import(self):
        import fusion_finance
        assert fusion_finance.__version__ == "0.1.0"

    def test_cli_import(self):
        from fusion_finance import cli
        assert cli.main is not None