from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from .config import DEFAULT_MLX_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

_HAS_FUSION_CORE = False
try:
    from fusion_core import FusionMLXClient

    _HAS_FUSION_CORE = True
    logger.info("fusion_core available, using FusionMLXClient")
except ImportError:
    logger.info("fusion_core not available, falling back to httpx")


def _resolve_api_key(explicit: str = "") -> str:
    if explicit:
        return explicit
    key = os.environ.get("FUSION_MLX_API_KEY", "")
    if key:
        return key
    try:
        cfg_path = Path.home() / ".fusion-mlx" / "settings.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            key = str(cfg.get("auth", {}).get("api_key", "") or "")
            if key:
                return key
    except Exception as e:
        logger.warning("read mlx settings.json failed: %s", e)
    return ""


class MLXClient:
    def __init__(self, base_url: str = "", model: str = "", max_retries: int = 2, api_key: str = ""):
        self.base_url = base_url or DEFAULT_MLX_BASE_URL
        self.default_model = model or DEFAULT_MODEL
        self.max_retries = max_retries
        self.api_key = _resolve_api_key(api_key)
        self._client: Any = None
        self._httpx_client: Any = None
        if _HAS_FUSION_CORE:
            self._client = FusionMLXClient(base_url=self.base_url)
        logger.info(
            "MLXClient initialized, base_url=%s, model=%s, fusion_core=%s, api_key=%s",
            self.base_url,
            self.default_model,
            _HAS_FUSION_CORE,
            "yes" if self.api_key else "no",
        )

    @property
    def httpx_client(self):
        if self._httpx_client is None:
            import httpx

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._httpx_client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0, headers=headers)
        return self._httpx_client

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.default_model
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                if _HAS_FUSION_CORE and self._client is not None:
                    response = await self._client.chat(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    content = response if isinstance(response, str) else str(response)
                else:
                    content = await self._chat_httpx(messages, model, temperature, max_tokens)
                logger.debug("chat response len=%d, attempt=%d", len(content), attempt)
                return content
            except Exception as e:
                last_err = e
                logger.warning("chat attempt %d failed: %s", attempt, e)
        logger.error("chat all retries exhausted: %s", last_err)
        return ""

    async def _chat_httpx(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        used_model = model
        if not used_model:
            try:
                resp = await self.httpx_client.get("/models")
                data = resp.json()
                available = data.get("data", [])
                if available:
                    used_model = available[0].get("id", available[0].get("model", ""))
            except Exception:
                used_model = DEFAULT_MODEL
        payload = {
            "model": used_model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = await self.httpx_client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        model = model or self.default_model
        if _HAS_FUSION_CORE and self._client is not None:
            try:
                async for chunk in self._client.chat_stream(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                return
            except AttributeError:
                logger.warning("chat_stream not supported by fusion_core, falling back")
        content = await self.chat(messages, model, temperature, max_tokens)
        yield content

    async def health_check(self) -> dict[str, Any]:
        try:
            if _HAS_FUSION_CORE and self._client is not None:
                models = await self._client.list_models()
                return {"status": "ok", "models": models}
            resp = await self.httpx_client.get("/models")
            resp.raise_for_status()
            data = resp.json()
            return {"status": "ok", "models": data.get("data", [])}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def close(self):
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
            self._httpx_client = None
