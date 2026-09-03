from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__
from ..ai_client import MLXClient
from ..config import DEFAULT_PORT, auth_safety_check, ensure_dirs, get_api_key, get_cors_origins, setup_logging
from ..copilot import CopilotEngine
from ..exceptions import AIClientError, DataError, FinanceError, ModelError, ReportError, RiskError
from .middleware import APIKeyMiddleware, AuditMiddleware, RateLimitMiddleware
from .routes import audit, chart, copilot, dashboard, data, health, modeling, project, report, risk, statements, ws
from .sse import router as sse_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    ensure_dirs()
    app.state.port = getattr(app.state, "port", DEFAULT_PORT)
    app.state.mlx_client = MLXClient()
    app.state.copilot_engine = CopilotEngine(app.state.mlx_client)
    bind_host = getattr(app.state, "host", "127.0.0.1")
    for w in auth_safety_check(bind_host):
        logger.warning("startup auth warning: %s", w)
    logger.info("Fusion-Finance API started on port %s", app.state.port)
    yield
    try:
        await app.state.mlx_client.close()
    except Exception as e:
        logger.warning("MLXClient close failed on shutdown: %s", e)
    logger.info("Fusion-Finance API shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fusion-Finance API",
        description="Local AI-powered financial analysis platform — Claude Finance domestic alternative",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.port = DEFAULT_PORT

    @app.exception_handler(FinanceError)
    async def finance_error_handler(request: Request, exc: FinanceError):
        error_type = "finance_error"
        status = 500
        if isinstance(exc, ModelError):
            error_type = f"model_error.{exc.model_type}" if exc.model_type else "model_error"
            status = 422
        elif isinstance(exc, DataError):
            error_type = f"data_error.{exc.field}" if exc.field else "data_error"
            status = 400
        elif isinstance(exc, RiskError):
            error_type = f"risk_error.{exc.risk_type}" if exc.risk_type else "risk_error"
            status = 422
        elif isinstance(exc, ReportError):
            error_type = f"report_error.{exc.report_type}" if exc.report_type else "report_error"
            status = 500
        elif isinstance(exc, AIClientError):
            error_type = "ai_client_error"
            status = 503
        detail = exc.safe_detail or exc.message or "internal error"
        logger.error(
            "FinanceError handled: %s | type=%s | detail=%s", exc.message, error_type, detail, exc_info=True
        )
        return JSONResponse(status_code=status, content={"error": error_type, "detail": detail})

    app.add_middleware(APIKeyMiddleware, api_key=get_api_key())
    rate_limit = int(os.getenv("FUSION_FINANCE_RATE_LIMIT", "100"))
    app.add_middleware(RateLimitMiddleware, max_requests=rate_limit, window_seconds=60)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "x-api-key", "x-auth-user"],
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
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(sse_router, prefix="/events", tags=["sse"])
    app.include_router(ws.router, prefix="/ws", tags=["websocket"])

    return app


app = create_app()
