from __future__ import annotations

import os

os.environ.setdefault("FUSION_FINANCE_DISABLE_AUTH", "1")
os.environ.setdefault("FUSION_FINANCE_API_KEY", "")
os.environ.setdefault("FUSION_FINANCE_HOST", "127.0.0.1")
os.environ.setdefault("FUSION_FINANCE_DATA_DIR", str(os.path.join(os.path.dirname(__file__), "..", ".test_data")))
os.environ.setdefault("FUSION_FINANCE_RATE_LIMIT", "1000000")

import pytest

TEST_API_KEY = os.environ.get("FUSION_FINANCE_API_KEY", "")


@pytest.fixture(autouse=True)
def _reset_app_state():
    from fusion_finance.api.app import app

    saved = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def api_key() -> str:
    return TEST_API_KEY


@pytest.fixture
def auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if TEST_API_KEY:
        headers["x-api-key"] = TEST_API_KEY
    return headers
