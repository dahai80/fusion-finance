from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any

from .engine import DCFModel

logger = logging.getLogger(__name__)

SCENARIO_PRESETS = {
    "bear": {"growth_adj": -0.3, "margin_adj": -0.05, "wacc_adj": 0.02},
    "base": {"growth_adj": 0, "margin_adj": 0, "wacc_adj": 0},
    "bull": {"growth_adj": 0.3, "margin_adj": 0.05, "wacc_adj": -0.01},
}


@dataclass
class Scenario:
    name: str = ""
    label: str = ""
    adjustments: dict[str, float] = field(default_factory=dict)
    model: DCFModel | None = None
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "adjustments": self.adjustments,
            "result": self.result,
        }


class ScenarioManager:
    def __init__(self, base_model: DCFModel):
        self.base_model = base_model
        self.base_result = base_model.calculate()
        self.scenarios: dict[str, Scenario] = {}
        for name, adj in SCENARIO_PRESETS.items():
            self.scenarios[name] = self._build_scenario(name, adj)

    def _build_scenario(self, name: str, adjustments: dict[str, float]) -> Scenario:
        scenario_model = copy.deepcopy(self.base_model)
        if "growth_adj" in adjustments:
            scenario_model.terminal_growth = max(0, scenario_model.terminal_growth + adjustments["growth_adj"])
        if "margin_adj" in adjustments and scenario_model.ebit_margin:
            scenario_model.ebit_margin = [m + adjustments["margin_adj"] for m in scenario_model.ebit_margin]
        if "wacc_adj" in adjustments:
            scenario_model.wacc = max(0.01, scenario_model.wacc + adjustments["wacc_adj"])
        result = scenario_model.calculate()
        labels = {"bear": "悲观", "base": "基准", "bull": "乐观"}
        return Scenario(
            name=name, label=labels.get(name, name), adjustments=adjustments, model=scenario_model, result=result
        )

    def add_scenario(self, name: str, adjustments: dict[str, float], label: str = "") -> Scenario:
        scenario = self._build_scenario(name, adjustments)
        if label:
            scenario.label = label
        self.scenarios[name] = scenario
        logger.info("Added scenario: %s, adjustments=%s", name, adjustments)
        return scenario

    def remove_scenario(self, name: str) -> bool:
        if name in self.scenarios:
            del self.scenarios[name]
            logger.info("Removed scenario: %s", name)
            return True
        return False

    def compare(self) -> dict[str, Any]:
        return {name: s.result for name, s in self.scenarios.items()}

    def get_summary(self) -> list[dict[str, Any]]:
        summary = []
        for name, s in self.scenarios.items():
            ev = s.result.get("equity_value", 0)
            base_ev = self.base_result.get("equity_value", 0)
            delta_pct = ((ev - base_ev) / base_ev * 100) if base_ev else 0
            summary.append(
                {
                    "name": name,
                    "label": s.label,
                    "equity_value": ev,
                    "target_price": s.result.get("target_price", 0),
                    "delta_pct": round(delta_pct, 1),
                }
            )
        return summary

    def get_scenario(self, name: str) -> Scenario | None:
        return self.scenarios.get(name)
