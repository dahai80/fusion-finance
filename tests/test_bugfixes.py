import os
import tempfile

from fusion_finance.modeling.portfolio import TechnicalIndicators
from fusion_finance.report.formatter import ReportFormatter
from fusion_finance.risk.advanced_risk import RiskModelingEngine


def _prices(n):
    return [100 + i * 0.5 + ((i % 3) - 1) * 2 for i in range(n)]


class TestMacdShortSeries:
    def test_macd_returns_empty_when_too_short(self):
        for n in (5, 20, 26, 30):
            res = TechnicalIndicators.macd(_prices(n))
            assert res == [], f"n={n} should return empty, got len={len(res)}"

    def test_macd_no_index_error_boundary(self):
        res = TechnicalIndicators.macd(_prices(34))
        assert len(res) > 0
        assert set(res[0].keys()) == {"macd", "signal", "histogram"}

    def test_macd_grows_with_length(self):
        r34 = TechnicalIndicators.macd(_prices(34))
        r50 = TechnicalIndicators.macd(_prices(50))
        assert len(r50) > len(r34)


class TestStressTestMitigationsType:
    def test_all_scenarios_have_list_mitigations(self):
        scenarios = RiskModelingEngine().stress_test_scenarios()
        assert len(scenarios) >= 3
        for s in scenarios:
            assert isinstance(s.mitigations, list), f"{s.scenario} mitigations not list"
            assert all(isinstance(m, str) for m in s.mitigations)

    def test_credit_spread_scenario_mitigations(self):
        scenarios = RiskModelingEngine().stress_test_scenarios()
        credit = [s for s in scenarios if "信用" in s.scenario][0]
        assert credit.mitigations == ["分散信用敞口", "增持高评级债"]
        assert len(credit.mitigations) == 2


class TestExportFallbackPaths:
    def test_pdf_fallback_returns_html(self):
        d = tempfile.mkdtemp()
        try:
            ret = ReportFormatter().export("content", "pdf", os.path.join(d, "r.pdf"))
            assert ret.endswith(".html")
            assert os.path.exists(ret)
            assert not os.path.exists(os.path.join(d, "r.pdf"))
        finally:
            import shutil

            shutil.rmtree(d)

    def test_pptx_returns_existing_path(self):
        d = tempfile.mkdtemp()
        try:
            ret = ReportFormatter().export("content", "pptx", os.path.join(d, "r.pptx"))
            assert os.path.exists(ret), f"returned path does not exist: {ret}"
            assert ret.endswith((".pptx", ".txt"))
        finally:
            import shutil

            shutil.rmtree(d)

    def test_xlsx_returns_existing_path(self):
        d = tempfile.mkdtemp()
        try:
            ret = ReportFormatter().export("content", "xlsx", os.path.join(d, "r.xlsx"))
            assert os.path.exists(ret), f"returned path does not exist: {ret}"
            assert ret.endswith((".xlsx", ".csv"))
        finally:
            import shutil

            shutil.rmtree(d)
