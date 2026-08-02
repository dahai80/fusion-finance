from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SVG_WIDTH = 800
SVG_HEIGHT = 500
MARGIN = {"top": 40, "right": 30, "bottom": 60, "left": 70}


def _svg_wrap(content: str, width: int = 0, height: int = 0, title: str = "") -> str:
    w = width or SVG_WIDTH
    h = height or SVG_HEIGHT
    title_el = f"<title>{title}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n{title_el}\n'
        f'<rect width="{w}" height="{h}" fill="#1a1a2e"/>\n{content}\n</svg>'
    )


def _plot_area() -> dict[str, float]:
    m = MARGIN
    return {
        "x": m["left"],
        "y": m["top"],
        "w": SVG_WIDTH - m["left"] - m["right"],
        "h": SVG_HEIGHT - m["top"] - m["bottom"],
    }


def render_candlestick(ohlcv: list[dict[str, float]], title: str = "Price Chart") -> str:
    if not ohlcv:
        return _svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

    pa = _plot_area()
    n = len(ohlcv)
    all_high = [b.get("high", 0) for b in ohlcv]
    all_low = [b.get("low", 0) for b in ohlcv]
    pmin, pmax = min(all_low), max(all_high)
    prange = pmax - pmin if pmax != pmin else 1

    bar_w = pa["w"] / n * 0.6
    gap = pa["w"] / n

    def price_y(p: float) -> float:
        return pa["y"] + pa["h"] - (p - pmin) / prange * pa["h"]

    elements = []
    for i, bar in enumerate(ohlcv):
        x = pa["x"] + i * gap + gap / 2
        o, h, low, c = bar.get("open", 0), bar.get("high", 0), bar.get("low", 0), bar.get("close", 0)
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

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
    return _svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
