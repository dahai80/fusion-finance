import logging

import pytest

from fusion_finance.api.app import create_app
from fusion_finance.exceptions import (
    AIClientError,
    DataError,
    FinanceError,
    ModelError,
    ReportError,
    RiskError,
)


class TestExceptionHierarchy:
    def test_finance_error_base(self):
        err = FinanceError("boom", "detail-x")
        assert err.message == "boom"
        assert err.detail == "detail-x"
        assert isinstance(err, Exception)

    def test_finance_error_default_detail(self):
        err = FinanceError("only-msg")
        assert err.detail == "only-msg"

    def test_model_error(self):
        err = ModelError("bad model", model_type="dcf")
        assert err.model_type == "dcf"
        assert err.detail == "bad model"
        assert isinstance(err, FinanceError)

    def test_data_error(self):
        err = DataError("bad data", field="revenue")
        assert err.field == "revenue"
        assert isinstance(err, FinanceError)

    def test_risk_error(self):
        err = RiskError("risk hit", risk_type="kyc")
        assert err.risk_type == "kyc"
        assert isinstance(err, FinanceError)

    def test_report_error(self):
        err = ReportError("report fail", report_type="valuation")
        assert err.report_type == "valuation"
        assert isinstance(err, FinanceError)

    def test_ai_client_error(self):
        err = AIClientError("mlx down")
        assert err.provider == "fusion-mlx"
        assert isinstance(err, FinanceError)

    def test_ai_client_error_custom_provider(self):
        err = AIClientError("down", provider="openai")
        assert err.provider == "openai"

    def test_raise_and_catch(self):
        with pytest.raises(ModelError) as ei:
            raise ModelError("x", model_type="ddm")
        assert ei.value.model_type == "ddm"


class TestAPIExceptionHandler:
    @pytest.fixture
    def client(self):
        from httpx import ASGITransport, AsyncClient

        app = create_app()

        @app.get("/__raise/{kind}")
        async def raise_err(kind: str):
            if kind == "model":
                raise ModelError("m", model_type="dcf")
            if kind == "data":
                raise DataError("d", field="revenue")
            if kind == "risk":
                raise RiskError("r", risk_type="kyc")
            if kind == "report":
                raise ReportError("rp", report_type="val")
            if kind == "ai":
                raise AIClientError("ai")
            raise FinanceError("base")

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_model_error_status(self, client):
        r = await client.get("/__raise/model")
        assert r.status_code == 422
        body = r.json()
        assert body["error"] == "model_error.dcf"
        assert body["detail"] == "m"

    @pytest.mark.asyncio
    async def test_data_error_status(self, client):
        r = await client.get("/__raise/data")
        assert r.status_code == 400
        assert r.json()["error"] == "data_error.revenue"

    @pytest.mark.asyncio
    async def test_risk_error_status(self, client):
        r = await client.get("/__raise/risk")
        assert r.status_code == 422
        assert r.json()["error"] == "risk_error.kyc"

    @pytest.mark.asyncio
    async def test_report_error_status(self, client):
        r = await client.get("/__raise/report")
        assert r.status_code == 500
        assert r.json()["error"] == "report_error.val"

    @pytest.mark.asyncio
    async def test_ai_client_error_status(self, client):
        r = await client.get("/__raise/ai")
        assert r.status_code == 503
        assert r.json()["error"] == "ai_client_error"

    @pytest.mark.asyncio
    async def test_base_finance_error_status(self, client):
        r = await client.get("/__raise/base")
        assert r.status_code == 500
        assert r.json()["error"] == "finance_error"

    @pytest.mark.asyncio
    async def test_error_without_subtype_field(self, client):
        from httpx import ASGITransport, AsyncClient

        app = create_app()

        @app.get("/__bare")
        async def bare():
            raise ModelError("m")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/__bare")
            assert r.status_code == 422
            assert r.json()["error"] == "model_error"


def test_exceptions_log(caplog):
    with caplog.at_level(logging.ERROR, logger="fusion_finance.exceptions"):
        ModelError("logged", model_type="lbo")
    assert any("ModelError" in rec.message for rec in caplog.records)
