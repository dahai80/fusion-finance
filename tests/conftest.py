from __future__ import annotations

import logging
import os
import shutil

import pytest

os.environ.setdefault("FUSION_FINANCE_DISABLE_AUTH", "1")
os.environ.setdefault("FUSION_FINANCE_API_KEY", "")
os.environ.setdefault("FUSION_FINANCE_HOST", "127.0.0.1")
os.environ.setdefault("FUSION_FINANCE_DATA_DIR", str(os.path.join(os.path.dirname(__file__), "..", ".test_data")))
os.environ.setdefault("FUSION_FINANCE_RATE_LIMIT", "1000000")

# deterministic key resolution: strip host key-chain env so tests only see keys they set themselves
for _var in ("FUSION_CLIENT_KEY", "FUSION_MLX_API_KEY", "MLX_API_KEY", "FUSION_GATEWAY_API_KEY"):
    os.environ.pop(_var, None)
os.environ.setdefault("FUSION_PROFILE", "dev")

TEST_API_KEY = os.environ.get("FUSION_FINANCE_API_KEY", "")

logger = logging.getLogger(__name__)


# purge test process data so it cannot pile up at the repo root (issue #34);
# set FUSION_FINANCE_KEEP_TEST_DATA=1 to keep the last run for debugging
@pytest.fixture(scope="session", autouse=True)
def _purge_test_data():
    data_dir = os.path.join(os.path.dirname(__file__), "..", ".test_data")

    def _purge(reason: str) -> None:
        if os.path.isdir(data_dir):
            shutil.rmtree(data_dir, ignore_errors=True)
            logger.info("purged %s (%s)", data_dir, reason)

    _purge("session start")
    yield
    if os.environ.get("FUSION_FINANCE_KEEP_TEST_DATA", "").lower() in ("1", "true", "yes"):
        logger.info("keeping %s (FUSION_FINANCE_KEEP_TEST_DATA set)", data_dir)
    else:
        _purge("session end")


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
