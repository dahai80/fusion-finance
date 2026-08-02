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


def render_waterfall(categories: list[str], values: list[float], title: str = "Bridge Analysis") -> str:
    if not categories:
        return _svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

    pa = _plot_area()
    n = len(categories)
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
            f'<text x="{label_x:.1f}" y="{pa["y"] + pa["h"] + 20:.1f}" fill="#ccc" text-anchor="middle" font-size="10">{bar["category"]}</text>'
        )
        val_label = f"+{bar['value']:.1f}" if bar["value"] >= 0 else f"{bar['value']:.1f}"
        elements.append(
            f'<text x="{label_x:.1f}" y="{y_top - 5:.1f}" fill="#eee" text-anchor="middle" font-size="10">{val_label}</text>'
        )

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
    return _svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
