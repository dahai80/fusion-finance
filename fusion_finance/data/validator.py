from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataValidator:
    REQUIRED_FINANCIAL_FIELDS = ["revenue", "net_income", "total_assets", "total_liabilities", "equity"]

    def validate_row(self, row: dict[str, Any], required_fields: list[str] | None = None) -> tuple[bool, list[str]]:
        fields = required_fields or []
        errors = []
        for field in fields:
            if field not in row or row[field] is None:
                errors.append(f"Missing required field: {field}")
        for field in fields:
            val = row.get(field)
            if val is not None and isinstance(val, str):
                try:
                    float(val)
                except ValueError:
                    errors.append(f"Non-numeric value for field '{field}': {val}")
        return (len(errors) == 0, errors)

    def validate_dataset(
        self, data: list[dict[str, Any]], required_fields: list[str] | None = None
    ) -> tuple[int, list[dict[str, Any]]]:
        valid_count = 0
        all_errors = []
        for i, row in enumerate(data):
            ok, errors = self.validate_row(row, required_fields)
            if ok:
                valid_count += 1
            else:
                all_errors.append({"row": i, "errors": errors})
        logger.info("Validated %d rows: %d valid, %d invalid", len(data), valid_count, len(all_errors))
        return (valid_count, all_errors)

    def validate_balance_sheet(
        self, assets: float, liabilities: float, equity: float, tolerance: float = 0.01
    ) -> tuple[bool, str]:
        if assets is None or liabilities is None or equity is None:
            return (False, "Balance sheet validation skipped: missing values")
        diff = abs(assets - liabilities - equity)
        tol = max(0.01, abs(assets) * 0.01) if tolerance == 0.01 else tolerance
        if diff <= tol:
            return (True, "Balance sheet balanced")
        return (
            False,
            f"Balance sheet imbalance: assets({assets}) != liabilities({liabilities}) + equity({equity}), diff={diff:.4f}",
        )

    def sanitize_numeric(self, value: Any, default: float | None = 0.0) -> float | None:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("$", "").replace(" ", "").replace("(", "-").replace(")", "")
            if cleaned == "":
                return default
            try:
                return float(cleaned)
            except ValueError:
                logger.warning("sanitize_numeric: cannot parse %r; returning default %r", value, default)
                return default
        logger.warning(
            "sanitize_numeric: unsupported type %s for value %r; returning default %r",
            type(value).__name__,
            value,
            default,
        )
        return default

    def check_completeness(
        self, data: list[dict[str, Any]], required_fields: list[str] | None = None
    ) -> dict[str, float]:
        if not data:
            return {}
        fields = required_fields or self.REQUIRED_FINANCIAL_FIELDS
        result = {}
        for field in fields:
            present = sum(1 for row in data if field in row and row[field] is not None)
            result[field] = present / len(data)
        return result
