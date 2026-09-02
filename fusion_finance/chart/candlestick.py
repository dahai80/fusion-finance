from __future__ import annotations

import logging

from ..exceptions import FinanceError
from ._common import MAX_CELLS, SVG_WIDTH, _empty_svg, _esc, _plot_area, _svg_wrap

logger = logging.getLogger(__name__)

_REQUIRED_OHLCV_FIELDS = ("open", "high", "low", "close")


def render_candlestick(ohlcv: list[dict[str, float]], title: str = "Price Chart") -> str:
    if not ohlcv:
        return _empty_svg(title)

    n = len(ohlcv)
    if n > MAX_CELLS:
        logger.warning("candlestick cell budget exceeded: %d > %d", n, MAX_CELLS)
        raise FinanceError(message="chart cell budget exceeded", detail=f"candlestick {n} bars > {MAX_CELLS}")
    for i, bar in enumerate(ohlcv):
        if not isinstance(bar, dict):
            raise FinanceError(message="chart input dimension mismatch", detail=f"ohlcv[{i}] is not a dict")
        missing = [f for f in _REQUIRED_OHLCV_FIELDS if f not in bar]
        if missing:
            raise FinanceError(message="chart input dimension mismatch", detail=f"ohlcv[{i}] missing fields {missing}")

    pa = _plot_area()
    all_high = [b["high"] for b in ohlcv]
    all_low = [b["low"] for b in ohlcv]
    pmin, pmax = min(all_low), max(all_high)
    prange = pmax - pmin if pmax != pmin else 1

    bar_w = pa["w"] / n * 0.6
    gap = pa["w"] / n

    def price_y(p: float) -> float:
        return pa["y"] + pa["h"] - (p - pmin) / prange * pa["h"]

    elements = []
    for i, bar in enumerate(ohlcv):
        x = pa["x"] + i * gap + gap / 2
        o, h, low, c = bar["open"], bar["high"], bar["low"], bar["close"]
        is_up = c >= o
        color = "#26a69a" if is_up else "#ef5350"
        fill = color if not is_up else "none"

        elements.append(
            f'<line x1="{x:.1f}" y1="{price_y(h):.1f}" x2="{x:.1f}" y2="{price_y(low):.1f}" stroke="{color}" stroke-width="1.5"/>'
        )
        elements.append(
            f'<rect x="{x - bar_w / 2:.1f}" y="{price_y(max(o, c)):.1f}" width="{bar_w:.1f}" '
            f'height="{abs(price_y(o) - price_y(c)) or 1:.1f}" fill="{fill}" stroke="{color}" stroke-width="1"/>'
        )

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{_esc(title)}</text>'
    return _svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
