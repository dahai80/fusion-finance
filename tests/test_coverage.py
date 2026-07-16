"""Fusion-Finance 全覆盖测试。"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from fusion_finance.modeling import FinancialModelingEngine, DCFModel, CompsAnalysis, AdvancedModelingEngine, LBOModel, DDMModel, MergerModel
from fusion_finance.statements import StatementAnalyzer, FinancialStatement, FinancialAnalysis
from fusion_finance.risk import RiskComplianceEngine, KYCCheck, CreditAssessment, RiskModelingEngine, VaRResult, StressTestResult
from fusion_finance.report import ReportGenerator
from fusion_finance.utils import AuditTrail, AuditEntry


class TestDCFDeep:
    def test_dcf_default_ebit_margin(self):
        model = DCFModel(company="T", revenue=[100, 120, 140], forecast_years=3)
        result = model.calculate()
        assert result["enterprise_value"] > 0

    def test_dcf_with_net_debt(self):
        model = DCFModel(company="T", revenue=[100, 120], ebit_margin=[0.2, 0.22],
                        net_debt=50, shares_outstanding=10, wacc=0.12, terminal_growth=0.02)
        result = model.calculate()
        assert result["target_price"] > 0

    def test_dcf_single_year(self):
        model = DCFModel(company="T", revenue=[100], ebit_margin=[0.2])
        result = model.calculate()
        assert result["pv_fcf"] > 0


class TestLBO:
    def test_lbo_calculation(self):
        model = LBOModel(company="T", purchase_price=1000, ebitda=[100, 120, 140, 160, 180],
                        debt_pct=0.6, exit_multiple=10, exit_year=5)
        result = model.calculate()
        assert result["moic"] > 0
        assert result["irr"] > 0

    def test_lbo_no_ebitda(self):
        model = LBOModel(company="T")
        result = model.calculate()
        assert "error" in result

    def test_lbo_zero_equity(self):
        model = LBOModel(company="T", purchase_price=100, ebitda=[10, 20],
                        equity_pct=0, exit_year=3)
        result = model.calculate()
        assert result["moic"] == 0


class TestDDM:
    def test_ddm_calculation(self):
        model = DDMModel(company="T", current_dividend=2.0, growth_rate=0.05, required_return=0.10)
        result = model.calculate()
        assert result["fair_value"] == 42.0

    def test_ddm_invalid_growth(self):
        model = DDMModel(company="T", current_dividend=2.0, growth_rate=0.10, required_return=0.08)
        result = model.calculate()
        assert "error" in result


class TestMerger:
    def test_merger_calculation(self):
        model = MergerModel(acquirer="A", target="T", acquirer_price=50, target_price=30, premium=0.3)
        result = model.calculate()
        assert result["offer_price"] == 39.0
        assert result["premium"] == 30.0


class TestAdvancedModeling:
    @pytest.mark.asyncio
    async def test_build_lbo(self):
        engine = AdvancedModelingEngine()
        model = await engine.build_lbo("Test", [100, 120, 140])
        assert model.company == "Test"


class TestVaR:
    def test_var_calculation(self):
        import random
        returns = [random.gauss(0, 0.02) for _ in range(1000)]
        result = RiskModelingEngine.calculate_var(returns, portfolio_value=1_000_000)
        assert result.var_95 < 0
        assert result.var_99 < result.var_95

    def test_var_empty_returns(self):
        result = RiskModelingEngine.calculate_var([], portfolio_value=1_000_000)
        assert result.var_95 == 0

    def test_monte_carlo_var(self):
        import random
        result = RiskModelingEngine.monte_carlo_var(1_000_000, 0.10, 0.20, simulations=500)
        assert result.simulations == 500

    def test_stress_test_scenarios(self):
        scenarios = RiskModelingEngine.stress_test_scenarios()
        assert len(scenarios) >= 3


class TestStatementDeep:
    def test_metrics_zero_values(self):
        stmt = FinancialStatement(company="T", revenue=100)
        analyzer = StatementAnalyzer()
        analysis = analyzer.calculate_metrics(stmt)
        assert analysis.gross_margin == 0
        assert analysis.net_margin == 0

    def test_validate_balance_sheet_empty(self):
        analyzer = StatementAnalyzer()
        issues = analyzer.validate_balance_sheet([])
        assert issues == []

    @pytest.mark.asyncio
    async def test_analyze_statements(self):
        analyzer = StatementAnalyzer()
        result = await analyzer.analyze_statements("Test", {"revenue": 1000})
        assert isinstance(result, dict)


class TestRiskDeep:
    def test_kyc_defaults(self):
        kyc = KYCCheck(entity="Test")
        assert kyc.risk_level == "medium"
        assert kyc.risk_score == 50.0

    def test_credit_defaults(self):
        credit = CreditAssessment(entity="Test", credit_score=75, rating="A")
        assert credit.rating == "A"
        assert credit.credit_score == 75

    @pytest.mark.asyncio
    async def test_kyc_screening(self):
        engine = RiskComplianceEngine()
        result = await engine.kyc_screening("Test")
        assert result.entity == "Test"

    @pytest.mark.asyncio
    async def test_credit_assessment(self):
        engine = RiskComplianceEngine()
        result = await engine.credit_assessment("Test", {"revenue": 1000})
        assert result.entity == "Test"

    @pytest.mark.asyncio
    async def test_compliance_check(self):
        engine = RiskComplianceEngine()
        result = await engine.compliance_check("Test")
        assert isinstance(result, dict)


class TestReportDeep:
    def test_valuation_report_full(self):
        dcf = DCFModel(company="Test", revenue=[100, 120, 140], ebit_margin=[0.2, 0.22, 0.25])
        dcf.calculate()
        comps = CompsAnalysis(company="Test", peers=[{"name": "Peer1", "pe": 15, "ev_ebitda": 10, "ps": 2}])
        gen = ReportGenerator()
        report = gen.generate_valuation_report("Test", dcf, comps)
        assert "Peer1" in report
        assert "DCF" in report

    def test_pitchbook(self):
        dcf = DCFModel(company="Test", revenue=[100, 120])
        dcf.calculate()
        gen = ReportGenerator()
        pb = gen.generate_pitchbook("Test", dcf, "科技")
        assert "投资亮点" in pb

    def test_save_report_custom_name(self, tmp_path):
        gen = ReportGenerator()
        path = gen.save_report("# Test", str(tmp_path), filename="custom.md")
        assert path.endswith("custom.md")

    @pytest.mark.asyncio
    async def test_research_report(self):
        gen = ReportGenerator()
        result = await gen.generate_research_report("Test", "科技", {"key": "value"})
        assert isinstance(result, str)


class TestAuditTrail:
    def test_record_and_query(self):
        audit = AuditTrail(log_path="/tmp/_test_audit.jsonl")
        audit.record("user1", "dcf_calc", "modeling", "DCF for Test")
        audit.record("user1", "report_gen", "report", "Generated report")
        audit.record("user2", "kyc_check", "risk", "KYC for Test")
        entries = audit.query(user="user1")
        assert len(entries) == 2
        entries2 = audit.query(action="kyc_check")
        assert len(entries2) == 1

    def test_get_stats(self):
        audit = AuditTrail(log_path="/tmp/_test_audit2.jsonl")
        audit.record("u1", "a1", "m1")
        audit.record("u2", "a2", "m2")
        stats = audit.get_stats()
        assert stats["total_entries"] == 2
        assert stats["unique_users"] == 2

    def test_entry_fields(self):
        entry = AuditEntry(timestamp=time.time(), user="u", action="a", module="m", details="d", status="success")
        assert entry.status == "success"


class TestCLICoverage:
    def test_cli_import(self):
        from fusion_finance import cli
        assert cli.main is not None

    def test_cli_help(self):
        from click.testing import CliRunner
        from fusion_finance.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_cli_model_dcf_help(self):
        from click.testing import CliRunner
        from fusion_finance.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["model", "dcf", "--help"])
        assert result.exit_code == 0


class TestModuleIntegrity:
    def test_all_exports(self):
        from fusion_finance.modeling import FinancialModelingEngine, DCFModel, CompsAnalysis, AdvancedModelingEngine, LBOModel, DDMModel, MergerModel
        from fusion_finance.statements import StatementAnalyzer, FinancialStatement, FinancialAnalysis
        from fusion_finance.risk import RiskComplianceEngine, KYCCheck, CreditAssessment, RiskModelingEngine, VaRResult, StressTestResult
        from fusion_finance.report import ReportGenerator
        from fusion_finance.utils import AuditTrail, AuditEntry
        assert True


class TestAIAsyncSuccess:
    """模拟 fusion-mlx 成功响应，覆盖 AI 方法的成功路径。"""

    @pytest.mark.asyncio
    async def test_build_dcf_success(self):
        engine = FinancialModelingEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"ebit_margin": [0.2, 0.22, 0.25], "tax_rate": 0.25, "wacc": 0.10, "terminal_growth": 0.03, "net_debt": 50, "shares": 10, "assumptions": {"key": "val"}}'
        engine.mlx.chat = mock_chat
        model = await engine.build_dcf("Test", [100, 120, 140])
        assert len(model.ebit_margin) == 3
        assert model.target_price > 0

    @pytest.mark.asyncio
    async def test_build_comps_success(self):
        engine = FinancialModelingEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"peers": [{"name": "P1", "pe": 15, "ev_ebitda": 10, "ps": 2, "revenue_growth": 0.1, "ebitda_margin": 0.2}], "target_pe": 14, "target_ev_ebitda": 9, "analysis": "ok"}'
        engine.mlx.chat = mock_chat
        comps = await engine.build_comps("Test", "科技")
        assert comps.avg_pe == 15.0

    @pytest.mark.asyncio
    async def test_analyze_statements_success(self):
        analyzer = StatementAnalyzer()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"revenue_growth": 0.15, "key_metrics": {"毛利率": "良好"}, "strengths": ["增长快"], "weaknesses": ["负债高"], "recommendations": ["降杠杆"], "quality_score": "B"}'
        analyzer.mlx.chat = mock_chat
        result = await analyzer.analyze_statements("Test", {"revenue": 1000})
        assert result["revenue_growth"] == 0.15

    @pytest.mark.asyncio
    async def test_risk_kyc_success(self):
        engine = RiskComplianceEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"risk_level": "low", "risk_score": 20, "findings": ["合规"], "recommendations": ["继续监控"]}'
        engine.mlx.chat = mock_chat
        result = await engine.kyc_screening("Test")
        assert result.risk_level == "low"
        assert result.risk_score == 20

    @pytest.mark.asyncio
    async def test_risk_credit_success(self):
        engine = RiskComplianceEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"credit_score": 85, "rating": "AA", "max_credit_line": 5000000, "strengths": ["低负债"], "concerns": ["行业周期"]}'
        engine.mlx.chat = mock_chat
        result = await engine.credit_assessment("Test", {"revenue": 1000})
        assert result.credit_score == 85

    @pytest.mark.asyncio
    async def test_risk_compliance_success(self):
        engine = RiskComplianceEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"compliant": true, "issues": [], "overall_risk": "low", "summary": "合规"}'
        engine.mlx.chat = mock_chat
        result = await engine.compliance_check("Test contract")
        assert result["compliant"] is True

    @pytest.mark.asyncio
    async def test_advanced_lbo_success(self):
        engine = AdvancedModelingEngine()
        async def mock_chat(messages, temperature=0.1, max_tokens=4096):
            return '{"purchase_price": 800, "debt_pct": 0.65, "exit_multiple": 9.5, "interest_rate": 0.045, "assumptions": {"revenue_growth": "5%"}}'
        engine.mlx.chat = mock_chat
        model = await engine.build_lbo("Test", [100, 120, 140])
        assert model.purchase_price == 800