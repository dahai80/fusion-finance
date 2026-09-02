from __future__ import annotations

import logging

from ..exceptions import FinanceError
from ._common import MAX_CELLS, SVG_WIDTH, _empty_svg, _esc, _plot_area, _svg_wrap

logger = logging.getLogger(__name__)


def render_heatmap(
    matrix: list[list[float]], row_labels: list[str], col_labels: list[str], title: str = "Sensitivity Matrix"
) -> str:
    if not matrix or not matrix[0]:
        return _empty_svg(title)

    rows = len(matrix)
    cols = len(matrix[0])
    if rows * cols > MAX_CELLS:
        logger.warning("heatmap cell budget exceeded: %d x %d = %d", rows, cols, rows * cols)
        raise FinanceError(message="chart cell budget exceeded", detail=f"heatmap {rows}x{cols} > {MAX_CELLS}")
    for i, row in enumerate(matrix):
        if len(row) != cols:
            raise FinanceError(
                message="chart input dimension mismatch", detail=f"heatmap row {i} length {len(row)} != {cols}"
            )
    if row_labels and len(row_labels) != rows:
        raise FinanceError(
            message="chart input dimension mismatch", detail=f"row_labels length {len(row_labels)} != {rows}"
        )
    if col_labels and len(col_labels) != cols:
        raise FinanceError(
            message="chart input dimension mismatch", detail=f"col_labels length {len(col_labels)} != {cols}"
        )

    pa = _plot_area()
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
                f'<text x="{x + cell_w / 2:.1f}" y="{y + cell_h / 2 + 5:.1f}" '
                f'fill="#eee" text-anchor="middle" font-size="11">{val:.1f}</text>'
            )

    row_labels_svg = []
    for i, label in enumerate(row_labels):
        y = pa["y"] + i * cell_h + cell_h / 2
        row_labels_svg.append(
            f'<text x="{pa["x"] - 5:.1f}" y="{y:.1f}" fill="#ccc" text-anchor="end" font-size="11">{_esc(label)}</text>'
        )

    col_labels_svg = []
    for j, label in enumerate(col_labels):
        x = pa["x"] + j * cell_w + cell_w / 2
        col_labels_svg.append(
            f'<text x="{x:.1f}" y="{pa["y"] - 8:.1f}" fill="#ccc" text-anchor="middle" font-size="11">{_esc(label)}</text>'
        )

    title_svg = f'<text x="{SVG_WIDTH / 2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{_esc(title)}</text>'

    content = title_svg + "\n" + "\n".join(col_labels_svg) + "\n" + "\n".join(row_labels_svg) + "\n" + "\n".join(cells)
    return _svg_wrap(content, title=title)
