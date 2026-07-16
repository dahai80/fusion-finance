"""Coverage tests for Fusion-Finance."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_finance.ai_client import MLXClient
from fusion_finance.modeling.engine import FinancialModelingEngine, DCFModel
from fusion_finance.risk.engine import RiskComplianceEngine, KYCCheck, CreditAssessment
from fusion_finance.report.reports import ReportGenerator


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