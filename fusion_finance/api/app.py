from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import ensure_dirs, setup_logging
from .routes import audit, chart, copilot, data, health, modeling, project, report, risk, statements, ws

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    ensure_dirs()
    logger.info("Fusion-Finance API started on port %s", app.state.port if hasattr(app.state, "port") else 8200)
    yield
    logger.info("Fusion-Finance API shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fusion-Finance API",
        description="Local AI-powered financial analysis platform — Claude Finance domestic alternative",
        version="0.2.1",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(modeling.router, prefix="/api/v1/modeling", tags=["modeling"])
    app.include_router(statements.router, prefix="/api/v1/statements", tags=["statements"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
    app.include_router(report.router, prefix="/api/v1/report", tags=["report"])
    app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["copilot"])
    app.include_router(chart.router, prefix="/api/v1/chart", tags=["chart"])
    app.include_router(project.router, prefix="/api/v1/project", tags=["project"])
    app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
    app.include_router(ws.router, prefix="/ws", tags=["websocket"])

    return app


app = create_app()
