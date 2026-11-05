from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from fusion_finance.api.app import create_app

PAGES = [
    ("/ui", "dashboard", "Dashboard"),
    ("/ui/modeling", "modeling", "DCF"),
    ("/ui/risk", "risk", "Monte Carlo VaR"),
    ("/ui/copilot", "copilot", "Copilot"),
]


class TestWebPages:
    @pytest.mark.parametrize("path,page,marker", PAGES)
    def test_page_renders(self, path, page, marker):
        client = TestClient(create_app())
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
        assert marker in resp.text
        assert f'data-page="{page}"' in resp.text

    def test_nav_links_present(self):
        client = TestClient(create_app())
        resp = client.get("/ui")
        for path in ("/ui/modeling", "/ui/risk", "/ui/copilot"):
            assert f'href="{path}"' in resp.text

    def test_version_injected(self):
        from fusion_finance import __version__

        client = TestClient(create_app())
        resp = client.get("/ui")
        assert f"v{__version__}" in resp.text

    def test_api_key_injected_when_configured(self, monkeypatch):
        monkeypatch.delenv("FUSION_FINANCE_DISABLE_AUTH", raising=False)
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")
        client = TestClient(create_app())
        resp = client.get("/ui")
        assert 'data-api-key="testkey123"' in resp.text

    def test_api_key_empty_when_auth_disabled(self):
        client = TestClient(create_app())
        resp = client.get("/ui")
        assert 'data-api-key=""' in resp.text


class TestWebStatic:
    def test_css_served(self):
        client = TestClient(create_app())
        resp = client.get("/ui/static/app.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]
        assert "--primary" in resp.text

    def test_js_served(self):
        client = TestClient(create_app())
        resp = client.get("/ui/static/app.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]
        assert "fetchJSON" in resp.text


class TestUIAuthExemption:
    def test_ui_accessible_without_key_when_auth_on(self, monkeypatch):
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")
        client = TestClient(create_app())
        assert client.get("/ui").status_code == 200
        assert client.get("/ui/modeling").status_code == 200
        assert client.get("/ui/static/app.css").status_code == 200

    def test_api_requires_key_when_auth_on(self, monkeypatch):
        monkeypatch.delenv("FUSION_FINANCE_DISABLE_AUTH", raising=False)
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")
        client = TestClient(create_app())
        resp = client.post("/api/v1/modeling/dcf/calculate", json={"company": "x", "revenue": [1]})
        assert resp.status_code == 401

    def test_api_accepts_key_header(self, monkeypatch):
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")
        client = TestClient(create_app())
        resp = client.post(
            "/api/v1/modeling/dcf/calculate",
            json={"company": "x", "revenue": [1, 2, 3]},
            headers={"x-api-key": "testkey123"},
        )
        assert resp.status_code == 200


class TestWSQueryAuth:
    def test_copilot_ws_accepts_query_param_key(self, monkeypatch):
        monkeypatch.delenv("FUSION_FINANCE_DISABLE_AUTH", raising=False)
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")

        async def fake_stream(*args, **kwargs):
            yield {"type": "text", "content": "hi"}

        with (
            patch("fusion_finance.api.routes.ws.get_mlx_client") as MockMLX,
            patch("fusion_finance.api.routes.ws.CopilotEngine") as MockEngine,
        ):
            MockMLX.return_value = MagicMock()
            MockEngine.return_value.chat_stream = fake_stream
            client = TestClient(create_app())
            with client.websocket_connect("/ws/copilot?api_key=testkey123") as ws:
                ws.send_json({"message": "hello"})
                assert ws.receive_json()["type"] == "thinking"

    def test_copilot_ws_rejects_wrong_query_key(self, monkeypatch):
        monkeypatch.delenv("FUSION_FINANCE_DISABLE_AUTH", raising=False)
        monkeypatch.setenv("FUSION_FINANCE_API_KEY", "testkey123")
        client = TestClient(create_app())
        with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws/copilot?api_key=wrong") as ws:
            ws.send_json({"message": "hello"})
            ws.receive_json()
