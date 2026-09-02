from __future__ import annotations

import logging

from fastapi import Request

from ..ai_client import MLXClient
from ..copilot import CopilotEngine

logger = logging.getLogger(__name__)


def get_mlx_client(request: Request) -> MLXClient:
    client = getattr(request.app.state, "mlx_client", None)
    if client is None:
        logger.warning("app.state.mlx_client missing, constructing ephemeral MLXClient")
        client = MLXClient()
        request.app.state.mlx_client = client
    return client


def get_copilot_engine(request: Request) -> CopilotEngine:
    engine = getattr(request.app.state, "copilot_engine", None)
    if engine is None:
        logger.warning("app.state.copilot_engine missing, constructing ephemeral CopilotEngine")
        engine = CopilotEngine(get_mlx_client(request))
        request.app.state.copilot_engine = engine
    return engine

