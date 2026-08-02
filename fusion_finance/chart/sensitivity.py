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


def render_sensitivity_tornado(
    base_value: float, sensitivities: dict[str, list[float]], title: str = "Tornado Chart"
) -> str:
    if not sensitivities:
        return _svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

    pa = _plot_area()
    items = sorted(sensitivities.items(), key=lambda x: abs(x[1][1] - x[1][0]), reverse=True)
    n = len(items)
    bar_h = pa["h"] / n * 0.6
    gap = pa["h"] / n

    all_vals = [v for vals in sensitivities.values() for v in vals] + [base_value]
    vmin, vmax = min(all_vals), max(all_vals)
    vrange = vmax - vmin if vmax != vmin else 1

    def val_x(v: float) -> float:
        return pa["x"] + (v - vmin) / vrange * pa["w"]

    elements = []
    base_x = val_x(base_value)
    elements.append(
        f'<line x1="{base_x:.1f}" y1="{pa["y"]:.1f}" x2="{base_x:.1f}" y2="{pa["y"] + pa["h"]:.1f}" stroke="#666" stroke-dasharray="4"/>'
    )

    for i, (label, vals) in enumerate(items):
        y = pa["y"] + i * gap + gap / 2 - bar_h / 2
        low_x = val_x(vals[0])
        high_x = val_x(vals[1])
        elements.append(
            f'<rect x="{low_x:.1f}" y="{y:.1f}" width="{base_x - low_x:.1f}" height="{bar_h:.1f}" fill="#ef5350" opacity="0.7"/>'
        )
        elements.append(
            f'<rect x="{base_x:.1f}" y="{y:.1f}" width="{high_x - base_x:.1f}" height="{bar_h:.1f}" fill="#26a69a" opacity="0.7"/>'
        )
        label_y = y + bar_h / 2 + 4
        elements.append(
            f'<text x="{pa["x"] - 5:.1f}" y="{label_y:.1f}" fill="#ccc" text-anchor="end" font-size="11">{label}</text>'
        )

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
    return _svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
