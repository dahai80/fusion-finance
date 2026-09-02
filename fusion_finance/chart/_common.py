from __future__ import annotations

import logging
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

SVG_WIDTH = 800
SVG_HEIGHT = 500
MARGIN = {"top": 40, "right": 30, "bottom": 60, "left": 70}
MAX_CELLS = 100000


def _esc(s: str) -> str:
    return escape(str(s))


def _svg_wrap(content: str, width: int = 0, height: int = 0, title: str = "") -> str:
    w = width or SVG_WIDTH
    h = height or SVG_HEIGHT
    title_el = f"<title>{_esc(title)}</title>" if title else ""
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


def _empty_svg(title: str) -> str:
    return _svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)
