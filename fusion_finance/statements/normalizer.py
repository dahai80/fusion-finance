from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from .analyzer import FinancialStatement

logger = logging.getLogger(__name__)

A_STOCK_MAPPING: dict[str, str] = {
    "营业收入": "revenue",
    "营业总收入": "revenue",
    "毛利润": "gross_profit",
    "营业利润": "operating_income",
    "净利润": "net_income",
    "资产总计": "total_assets",
    "负债合计": "total_liabilities",
    "所有者权益合计": "equity",
    "股东权益合计": "equity",
    "经营活动现金流": "operating_cf",
    "自由现金流": "free_cf",
}

HK_STOCK_MAPPING: dict[str, str] = {
    "revenue": "revenue",
    "turnover": "revenue",
    "gross_profit": "gross_profit",
    "operating_profit": "operating_income",
    "profit_for_year": "net_income",
    "total_assets": "total_assets",
    "total_liabilities": "total_liabilities",
    "total_equity": "equity",
    "net_cash_from_operating": "operating_cf",
    "free_cash_flow": "free_cf",
}

US_GAAP_MAPPING: dict[str, str] = {
    "total_revenue": "revenue",
    "revenues": "revenue",
    "gross_profit": "gross_profit",
    "operating_income": "operating_income",
    "operating_profit": "operating_income",
    "net_income": "net_income",
    "net_earnings": "net_income",
    "total_assets": "total_assets",
    "total_liabilities": "total_liabilities",
    "stockholders_equity": "equity",
    "total_equity": "equity",
    "cash_from_operations": "operating_cf",
    "free_cash_flow": "free_cf",
}

STANDARD_MAPPINGS: dict[str, dict[str, str]] = {
    "A": A_STOCK_MAPPING,
    "CN": A_STOCK_MAPPING,
    "HK": HK_STOCK_MAPPING,
    "US": US_GAAP_MAPPING,
}


class StatementNormalizer:
    def __init__(self, standard: str = "A"):
        self.standard = standard.upper()
        self.mapping = STANDARD_MAPPINGS.get(self.standard, US_GAAP_MAPPING)
        logger.info("Normalizer initialized: standard=%s, fields=%d", self.standard, len(self.mapping))

    def normalize(self, raw: dict[str, Any], company: str = "", period: str = "") -> FinancialStatement:
        mapped: dict[str, float] = {}
        for raw_key, raw_val in raw.items():
            canonical = self.mapping.get(raw_key)
            if canonical and isinstance(raw_val, (int, float)):
                mapped[canonical] = float(raw_val)
        stmt = FinancialStatement(
            company=company or raw.get("company", raw.get("公司名称", "")),
            period=period or raw.get("period", raw.get("报告期", "")),
            revenue=mapped.get("revenue", 0.0),
            gross_profit=mapped.get("gross_profit", 0.0),
            operating_income=mapped.get("operating_income", 0.0),
            net_income=mapped.get("net_income", 0.0),
            total_assets=mapped.get("total_assets", 0.0),
            total_liabilities=mapped.get("total_liabilities", 0.0),
            equity=mapped.get("equity", 0.0),
            operating_cf=mapped.get("operating_cf", 0.0),
            free_cf=mapped.get("free_cf", 0.0),
        )
        logger.debug("Normalized %d fields for %s", len(mapped), stmt.company)
        return stmt

    def normalize_multi(self, raw_list: list[dict[str, Any]], standard: str = "") -> list[FinancialStatement]:
        if standard and standard.upper() != self.standard:
            self.standard = standard.upper()
            self.mapping = STANDARD_MAPPINGS.get(self.standard, US_GAAP_MAPPING)
        return [self.normalize(raw) for raw in raw_list]

    @staticmethod
    def year_over_year(current: FinancialStatement, previous: FinancialStatement) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for field_name in (
            "revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "total_assets",
            "total_liabilities",
            "equity",
        ):
            cur = getattr(current, field_name, 0)
            prev = getattr(previous, field_name, 0)
            if prev and prev != 0:
                result[f"{field_name}_yoy"] = round((cur - prev) / abs(prev) * 100, 2)
            else:
                result[f"{field_name}_yoy"] = None
        return result

    @staticmethod
    def quarter_over_quarter(current: FinancialStatement, previous: FinancialStatement) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for field_name in ("revenue", "gross_profit", "operating_income", "net_income"):
            cur = getattr(current, field_name, 0)
            prev = getattr(previous, field_name, 0)
            if prev and prev != 0:
                result[f"{field_name}_qoq"] = round((cur - prev) / abs(prev) * 100, 2)
            else:
                result[f"{field_name}_qoq"] = None
        return result

    @staticmethod
    def trend_analysis(statements: list[FinancialStatement]) -> dict[str, Any]:
        if len(statements) < 2:
            return {"error": "Need at least 2 periods for trend analysis"}
        sorted_stmts = sorted(statements, key=lambda s: s.period)
        metrics = ("revenue", "net_income", "operating_income")
        trends: dict[str, Any] = {}
        for metric in metrics:
            values = [getattr(s, metric, 0) for s in sorted_stmts]
            if not any(values):
                continue
            growth_rates = []
            for i in range(1, len(values)):
                if values[i - 1] and values[i - 1] != 0:
                    growth_rates.append(round((values[i] - values[i - 1]) / abs(values[i - 1]) * 100, 2))
                else:
                    growth_rates.append(None)
            avg_growth = None
            valid_rates = [g for g in growth_rates if g is not None]
            if valid_rates:
                avg_growth = round(sum(valid_rates) / len(valid_rates), 2)
            direction = "stable"
            if valid_rates:
                if all(g > 0 for g in valid_rates):
                    direction = "up"
                elif all(g < 0 for g in valid_rates):
                    direction = "down"
            trends[metric] = {
                "values": values,
                "growth_rates": growth_rates,
                "avg_growth": avg_growth,
                "direction": direction,
                "periods": [s.period for s in sorted_stmts],
            }
        logger.info("Trend analysis: %d metrics over %d periods", len(trends), len(sorted_stmts))
        return trends

    @staticmethod
    def to_dict(stmt: FinancialStatement) -> dict[str, Any]:
        return asdict(stmt)

    @staticmethod
    def list_standards() -> list[dict[str, str]]:
        return [
            {"code": "A", "name": "A股 (中国会计准则)", "field_count": len(A_STOCK_MAPPING)},
            {"code": "HK", "name": "港股 (HKFRS)", "field_count": len(HK_STOCK_MAPPING)},
            {"code": "US", "name": "美股 (US GAAP)", "field_count": len(US_GAAP_MAPPING)},
        ]
