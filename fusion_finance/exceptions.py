from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_GENERIC_DETAIL = "internal error"


def _safe_detail(detail: str) -> str:
    if not detail:
        return ""
    if len(detail) > 200:
        return detail[:200] + "..."
    return detail


class FinanceError(Exception):
    def __init__(self, message: str = "", detail: str = ""):
        self.message = message
        self.detail = detail or message
        self.safe_detail = _safe_detail(self.detail) if self.detail else ""
        super().__init__(message)
        logger.error("FinanceError: %s", message)


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
