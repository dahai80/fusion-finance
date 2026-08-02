from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ChartRenderer:
    SVG_WIDTH = 800
    SVG_HEIGHT = 500
    MARGIN = {"top": 40, "right": 30, "bottom": 60, "left": 70}

    def _svg_wrap(self, content: str, width: int = 0, height: int = 0, title: str = "") -> str:
        w = width or self.SVG_WIDTH
        h = height or self.SVG_HEIGHT
        title_el = f"<title>{title}</title>" if title else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n{title_el}\n'
            f'<rect width="{w}" height="{h}" fill="#1a1a2e"/>\n{content}\n</svg>'
        )

    def _plot_area(self) -> dict[str, float]:
        m = self.MARGIN
        return {
            "x": m["left"],
            "y": m["top"],
            "w": self.SVG_WIDTH - m["left"] - m["right"],
            "h": self.SVG_HEIGHT - m["top"] - m["bottom"],
        }

    def heatmap(self, matrix: list[list[float]], row_labels: list[str], col_labels: list[str], title: str = "Sensitivity Matrix") -> str:
        if not matrix or not matrix[0]:
            return self._svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

        pa = self._plot_area()
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

        title_svg = f'<text x="{self.SVG_WIDTH/2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'

        content = title_svg + "\n" + "\n".join(col_labels_svg) + "\n" + "\n".join(row_labels_svg) + "\n" + "\n".join(cells)
        return self._svg_wrap(content, title=title)

    def candlestick(self, ohlcv: list[dict[str, float]], title: str = "Price Chart") -> str:
        if not ohlcv:
            return self._svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

        pa = self._plot_area()
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
                f'<rect x="{x - bar_w/2:.1f}" y="{price_y(max(o, c)):.1f}" width="{bar_w:.1f}" '
                f'height="{abs(price_y(o) - price_y(c)) or 1:.1f}" fill="{fill}" stroke="{color}" stroke-width="1"/>'
            )

        title_svg = f'<text x="{self.SVG_WIDTH/2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
        return self._svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)

    def waterfall(self, categories: list[str], values: list[float], title: str = "Bridge Analysis") -> str:
        if not categories:
            return self._svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

        pa = self._plot_area()
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
        elements.append(f'<line x1="{pa["x"]:.1f}" y1="{zero_y:.1f}" x2="{pa["x"] + pa["w"]:.1f}" y2="{zero_y:.1f}" stroke="#666" stroke-dasharray="4"/>')

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

        title_svg = f'<text x="{self.SVG_WIDTH/2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
        return self._svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)

    def sensitivity_tornado(self, base_value: float, sensitivities: dict[str, list[float]], title: str = "Tornado Chart") -> str:
        if not sensitivities:
            return self._svg_wrap('<text x="400" y="250" fill="#888" text-anchor="middle">No data</text>', title=title)

        pa = self._plot_area()
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
        elements.append(f'<line x1="{base_x:.1f}" y1="{pa["y"]:.1f}" x2="{base_x:.1f}" y2="{pa["y"] + pa["h"]:.1f}" stroke="#666" stroke-dasharray="4"/>')

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

        title_svg = f'<text x="{self.SVG_WIDTH/2:.1f}" y="24" fill="#eee" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
        return self._svg_wrap(title_svg + "\n" + "\n".join(elements), title=title)
