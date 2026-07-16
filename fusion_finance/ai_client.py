"""fusion-mlx HTTP 客户端 — 所有 AI 推理的唯一接口。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MLXClient:
    def __init__(self, model: str = "", base_url: str = "http://localhost:8000/v1"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self._client

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: int = 4096) -> str:
        if not self.model:
            try:
                resp = await self.client.get("/models")
                data = resp.json()
                available = data.get("data", [])
                if available:
                    self.model = available[0].get("id", available[0].get("model", ""))
            except Exception:
                self.model = "qwen3.5-9b"
        payload = {
            "model": self.model or "qwen3.5-9b",
            "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
        }
        resp = await self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]