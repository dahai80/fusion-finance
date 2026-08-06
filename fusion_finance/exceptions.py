from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FinanceError(Exception):
    def __init__(self, message: str = "", detail: str = ""):
        self.message = message
        self.detail = detail or message
        super().__init__(message)
        logger.error("FinanceError: %s detail=%s", message, detail)


class ModelError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", model_type: str = ""):
        self.model_type = model_type
        super().__init__(message=message, detail=detail)
        logger.error("ModelError: type=%s %s", model_type, message)


class DataError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", field: str = ""):
        self.field = field
        super().__init__(message=message, detail=detail)
        logger.error("DataError: field=%s %s", field, message)


class RiskError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", risk_type: str = ""):
        self.risk_type = risk_type
        super().__init__(message=message, detail=detail)
        logger.error("RiskError: type=%s %s", risk_type, message)


class ReportError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", report_type: str = ""):
        self.report_type = report_type
        super().__init__(message=message, detail=detail)
        logger.error("ReportError: type=%s %s", report_type, message)


class AIClientError(FinanceError):
    def __init__(self, message: str = "", detail: str = "", provider: str = "fusion-mlx"):
        self.provider = provider
        super().__init__(message=message, detail=detail)
        logger.error("AIClientError: provider=%s %s", provider, message)
