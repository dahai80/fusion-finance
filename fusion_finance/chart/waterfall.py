from __future__ import annotations

import logging

from ..exceptions import FinanceError
from ._common import MAX_CELLS, SVG_WIDTH, _empty_svg, _esc, _plot_area, _svg_wrap

logger = logging.getLogger(__name__)


def render_waterfall(categories: list[str], values: list[float], title: str = "Bridge Analysis") -> str:
    if not categories:
        return _empty_svg(title)

    n = len(categories)
    if n > MAX_CELLS:
        logger.warning("waterfall cell budget exceeded: %d > %d", n, MAX_CELLS)
        raise FinanceError(message="chart cell budget exceeded", detail=f"waterfall {n} bars > {MAX_CELLS}")
    if len(values) != n:
        raise FinanceError(
            message="chart input dimension mismatch", detail=f"values length {len(values)} != categories length {n}"
        )

    pa = _plot_area()
    bar_w = pa["w"] / n * 0.7
    gap = pa["w"] / n

    running = 0.0
    bars = []
    for cat, val in zip(categories, values):
        base = running
        running += val
        bars.append({"category": cat, "base": base, "value": val, "top": running})

    all_vals = [b["base"] for b in bars] + [b["top"] for b in bars]
    vmin = min(min(all_vals), 0)
    vmax = max(all_vals)
    vrange = vmax - vmin if vmax != vmin else 1

    def val_y(v: float) -> float:
        return pa["y"] + pa["h"] - (v - vmin) / vrange * pa["h"]

    elements = []
    zero_y = val_y(0)
    elements.append(
        f'<line x1="{pa["x"]:.1f}" y1="{zero_y:.1f}" x2="{pa["x"] + pa["w"]:.1f}" y2="{zero_y:.1f}" stroke="#666" stroke-dasharray="4"/>'
    )

    for i, bar in enumerate(bars):
        x = pa["x"] + i * gap + gap / 2 - bar_w / 2
        y_top = val_y(max(bar["base"], bar["top"]))
        y_bot = val_y(min(bar["base"], bar["top"]))
        color = "#26a69a" if bar["value"] >= 0 else "#ef5350"
        elements.append(
            f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{y_bot - y_top or 1:.1f}" fill="{color}" opacity="0.85"/>'
        )
        label_x = pa["x"] + i * gap + gap / 2
        elements.append(
            f'<text x="{label_x:.1f}" y="{pa["y"] + pa["h"] + 20:.1f}" fill="#ccc" text-anchor="middle" font-size="10">{_esc(bar["category"])}</text>'
        )
        val_label = f"+{bar['value']:.1f}" if bar["value"] >= 0 else f"{bar['value']:.1f}"
        elements.append(
            f'<text x="{label_x:.1f}" y="{y_top - 5:.1f}" fill="#eee" text-anchor="middle" font-size="10">{val_label}</text>'
        )

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{_esc(title)}</text>'
    return _svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
