from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .cache import DataCache
from .csv_loader import CSVLoader
from .validator import DataValidator

logger = logging.getLogger(__name__)


class DataAdapter:
    def __init__(self, cache_ttl: int = 3600, cache_max: int = 256):
        self.loader = CSVLoader()
        self.validator = DataValidator()
        self.cache = DataCache(max_size=cache_max, default_ttl=cache_ttl)

    def load_csv(
        self,
        source: str | Path,
        delimiter: str = "",
        encoding: str = "",
        has_header: bool = True,
        required_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        cache_key = DataCache.make_key("csv", str(source), delimiter, encoding, has_header)
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("CSV cache hit: %s", source)
            return cached

        data = self.loader.load(source, delimiter=delimiter, encoding=encoding, has_header=has_header)
        valid_count, errors = self.validator.validate_dataset(data, required_fields)

        result = {
            "data": data,
            "row_count": len(data),
            "valid_rows": valid_count,
            "validation_errors": errors,
        }
        self.cache.set(cache_key, result)
        logger.info("CSV loaded: %s (%d rows, %d valid)", source, len(data), valid_count)
        return result

    def sanitize_row(self, row: dict[str, Any], numeric_fields: list[str] | None = None) -> dict[str, Any]:
        sanitized = {}
        fields = numeric_fields or list(row.keys())
        for key, val in row.items():
            if key in fields:
                sanitized[key] = self.validator.sanitize_numeric(val)
            else:
                sanitized[key] = val
        return sanitized

    def validate_balance(
        self, assets: float, liabilities: float, equity: float, tolerance: float = 0.01
    ) -> dict[str, Any]:
        ok, msg = self.validator.validate_balance_sheet(assets, liabilities, equity, tolerance)
        return {"balanced": ok, "message": msg}

    def check_completeness(
        self, data: list[dict[str, Any]], required_fields: list[str] | None = None
    ) -> dict[str, Any]:
        scores = self.validator.check_completeness(data, required_fields)
        overall = sum(scores.values()) / len(scores) if scores else 0.0
        return {"field_completeness": scores, "overall_score": overall}

    def invalidate(self, source: str) -> None:
        cache_key = DataCache.make_key("csv", source)
        self.cache.invalidate(cache_key)

    def clear_cache(self) -> None:
        self.cache.clear()
