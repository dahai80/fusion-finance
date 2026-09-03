from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_GENERIC_DETAIL = "internal error"
_PATH_RE = re.compile(r"/[^\s'\"<>]+")
_SECRET_RE = re.compile(r"(?i)(password|secret|token|api[_-]?key|authorization)\s*[=:]\s*\S+")


def _safe_detail(detail: str) -> str:
    if not detail:
        return ""
    redacted = _SECRET_RE.sub(r"\1=***", detail)
    redacted = _PATH_RE.sub("[path]", redacted)
    if len(redacted) > 200:
        redacted = redacted[:200] + "..."
    return redacted


class FinanceError(Exception):
    def __init__(self, message: str = "", detail: str = ""):
        self.message = message
        self.detail = detail or message
        self.safe_detail = _safe_detail(self.detail) if self.detail else ""
        super().__init__(message)
        logger.error("FinanceError: %s | detail=%s", message, self.safe_detail)


class ModelError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", model_type: str = ""):
        self.model_type = model_type
        super().__init__(message=message, detail=detail)


class DataError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", field: str = ""):
        self.field = field
        super().__init__(message=message, detail=detail)


class RiskError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", risk_type: str = ""):
        self.risk_type = risk_type
        super().__init__(message=message, detail=detail)


class ReportError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", report_type: str = ""):
        self.report_type = report_type
        super().__init__(message=message, detail=detail)


class AIClientError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", provider: str = "fusion-mlx"):
        self.provider = provider
        super().__init__(message=message, detail=detail)
