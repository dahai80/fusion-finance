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


def render_heatmap(matrix: list[list[float]], row_labels: list[str], col_labels: list[str], title: str = "Sensitivity Matrix") -> str:
    if not matrix or not matrix[0]:
        return _svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

    pa = _plot_area()
    rows = len(matrix)
    cols = len(matrix[0])
    cell_w = pa["w"] / cols
    cell_h = pa["h"] / rows

    all_vals = [v for row in matrix for v in row]
    vmin, vmax = min(all_vals), max(all_vals)
    vrange = vmax - vmin if vmax != vmin else 1

    cells = []
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            t = (val - vmin) / vrange
            r = int(255 * (1 - t))
            g = int(100 * t)
            b = int(255 * t)
            x = pa["x"] + j * cell_w
            y = pa["y"] + i * cell_h
            cells.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" '
                f'fill="rgb({r},{g},{b})" stroke="#333" stroke-width="0.5"/>'
            )
            cells.append(
                f'<text x="{x + cell_w/2:.1f}" y="{y + cell_h/2 + 5:.1f}" '
                f'fill="#eee" text-anchor="middle" font-size="11">{val:.1f}</text>'
            )

    row_labels_svg = []
    for i, label in enumerate(row_labels):
        y = pa["y"] + i * cell_h + cell_h / 2
        row_labels_svg.append(
            f'<text x="{pa["x"] - 5:.1f}" y="{y:.1f}" fill="#ccc" text-anchor="end" '
            f'font-size="11">{label}</text>'
        )

    col_labels_svg = []
    for j, label in enumerate(col_labels):
        x = pa["x"] + j * cell_w + cell_w / 2
        col_labels_svg.append(
            f'<text x="{x:.1f}" y="{pa["y"] - 8:.1f}" fill="#ccc" text-anchor="middle" '
            f'font-size="11">{label}</text>'
        )

    title_svg = f'<text x="{SVG_WIDTH/2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'

    content = title_svg + "\n" + "\n".join(col_labels_svg) + "\n" + "\n".join(row_labels_svg) + "\n" + "\n".join(cells)
    return _svg_wrap(content, title=title)
