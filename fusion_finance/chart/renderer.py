from __future__ import annotations

import logging

from .candlestick import render_candlestick
from .heatmap import render_heatmap
from .sensitivity import render_sensitivity_tornado
from .waterfall import render_waterfall

logger = logging.getLogger(__name__)


class ChartRenderer:
    def heatmap(
        self, matrix: list[list[float]], row_labels: list[str], col_labels: list[str], title: str = "Sensitivity Matrix"
    ) -> str:
        return render_heatmap(matrix, row_labels, col_labels, title)

    def candlestick(self, ohlcv: list[dict[str, float]], title: str = "Price Chart") -> str:
        return render_candlestick(ohlcv, title)

    def waterfall(self, categories: list[str], values: list[float], title: str = "Bridge Analysis") -> str:
        return render_waterfall(categories, values, title)

    def sensitivity_tornado(
        self, base_value: float, sensitivities: dict[str, list[float]], title: str = "Tornado Chart"
    ) -> str:
        return render_sensitivity_tornado(base_value, sensitivities, title)
