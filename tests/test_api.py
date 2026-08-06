"""API endpoint tests for Fusion-Finance."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fusion_finance.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoints:
    def test_health(self, client):
        resp = client.get("/api/v1/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.5.1"

    def test_ready(self, client):
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert "status" in resp.json()


class TestModelingEndpoints:
    def test_calculate_dcf(self, client):
        payload = {
            "company": "TestCorp",
            "revenue": [100, 120, 140],
            "wacc": 0.10,
            "terminal_growth": 0.03,
        }
        resp = client.post("/api/v1/modeling/dcf/calculate", json=payload)
        assert resp.status_code == 200
        assert "result" in resp.json()

    def test_sensitivity_analysis(self, client):
        payload = {
            "company": "TestCorp",
            "revenue": [100, 120, 140],
            "wacc": 0.10,
            "terminal_growth": 0.03,
            "wacc_range": [0.08, 0.10, 0.12],
            "growth_range": [0.02, 0.03, 0.04],
        }
        resp = client.post("/api/v1/modeling/sensitivity", json=payload)
        assert resp.status_code == 200
        assert "matrix" in resp.json()

    def test_portfolio_optimize(self, client):
        payload = {
            "assets": ["A", "B"],
            "returns": [0.10, 0.08],
            "volatilities": [0.20, 0.15],
            "correlations": [[1.0, 0.5], [0.5, 1.0]],
            "risk_free": 0.03,
        }
        resp = client.post("/api/v1/modeling/portfolio/optimize", json=payload)
        assert resp.status_code == 200

    def test_apv_calculate(self, client):
        payload = {
            "company": "TestCorp",
            "fcf": [100, 120, 140],
            "wacc": 0.10,
            "terminal_growth": 0.03,
            "debt": 500,
            "cost_of_debt": 0.06,
            "tax_rate": 0.25,
        }
        resp = client.post("/api/v1/modeling/apv", json=payload)
        assert resp.status_code == 200


class TestStatementEndpoints:
    def test_calculate_metrics(self, client):
        payload = {
            "income_statement": {
                "revenue": 1000,
                "cogs": 600,
                "operating_expenses": 200,
                "interest_expense": 50,
                "tax_rate": 0.25,
            },
            "balance_sheet": {
                "total_assets": 5000,
                "total_liabilities": 2000,
                "cash": 500,
                "current_assets": 1500,
                "current_liabilities": 800,
                "inventory": 300,
            },
            "cash_flow": {"operating_cf": 300, "capex": 100},
        }
        resp = client.post("/api/v1/statements/metrics", json=payload)
        assert resp.status_code == 200

    def test_validate(self, client):
        stmt = {
            "income_statement": {
                "revenue": 1000,
                "cogs": 600,
                "operating_expenses": 200,
                "interest_expense": 50,
                "tax_rate": 0.25,
            },
            "balance_sheet": {
                "total_assets": 5000,
                "total_liabilities": 2000,
                "cash": 500,
                "current_assets": 1500,
                "current_liabilities": 800,
                "inventory": 300,
            },
            "cash_flow": {"operating_cf": 300, "capex": 100},
        }
        payload = {"statements": [stmt]}
        resp = client.post("/api/v1/statements/validate", json=payload)
        assert resp.status_code == 200


class TestRiskEndpoints:
    def test_calculate_var(self, client):
        payload = {
            "returns": [0.01, -0.02, 0.03, -0.01, 0.02, 0.005, -0.015, 0.025],
            "portfolio_value": 1000000,
            "confidence_levels": [0.95, 0.99],
        }
        resp = client.post("/api/v1/risk/var", json=payload)
        assert resp.status_code == 200

    def test_stress_scenarios(self, client):
        resp = client.get("/api/v1/risk/stress-scenarios")
        assert resp.status_code == 200


class TestReportEndpoints:
    def test_valuation_report(self, client):
        payload = {
            "company": "TestCorp",
            "dcf_result": {"enterprise_value": 1000, "equity_value": 800},
            "comps_result": {"avg_pe": 15},
        }
        resp = client.post("/api/v1/report/valuation", json=payload)
        assert resp.status_code == 200

    def test_pitchbook(self, client):
        payload = {
            "company": "TestCorp",
            "industry": "Technology",
            "revenue": [1000, 1200, 1400],
            "ebit_margin": [0.2, 0.22, 0.24],
        }
        resp = client.post("/api/v1/report/pitchbook", json=payload)
        assert resp.status_code == 200


class TestDashboardEndpoints:
    def test_company_dashboard(self, client):
        payload = {
            "company": "TestCorp",
            "revenue": [100, 120, 140],
            "ebit_margin": [0.2, 0.22, 0.24],
            "wacc": 0.10,
            "terminal_growth": 0.03,
        }
        resp = client.post("/api/v1/dashboard/company", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"] == "TestCorp"
        assert "dcf" in data
        assert "scenarios" in data

    def test_company_dashboard_no_revenue(self, client):
        payload = {"company": "EmptyCorp"}
        resp = client.post("/api/v1/dashboard/company", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dcf"] is None

    def test_market_dashboard(self, client):
        resp = client.get("/api/v1/dashboard/market", params={"preset": "quality", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert "screener" in data

    def test_service_status(self, client):
        resp = client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "fusion-finance"
        assert "mlx" in data
        assert "modules" in data
