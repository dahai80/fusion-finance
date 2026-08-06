from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...chart import ChartRenderer
from ...exceptions import FinanceError

logger = logging.getLogger(__name__)

router = APIRouter()

_renderer = ChartRenderer()


class CandlestickRequest(BaseModel):
    symbol: str = ""
    data: list[dict[str, float]] = Field(default_factory=list)
    title: str = "Price Chart"


class HeatmapRequest(BaseModel):
    matrix: list[list[float]] = Field(default_factory=list)
    row_labels: list[str] = Field(default_factory=list)
    col_labels: list[str] = Field(default_factory=list)
    title: str = "Sensitivity Matrix"


class WaterfallRequest(BaseModel):
    categories: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    title: str = "Bridge Analysis"


class SensitivityChartRequest(BaseModel):
    factors: list[str] = Field(default_factory=list)
    low_values: list[float] = Field(default_factory=list)
    high_values: list[float] = Field(default_factory=list)
    base_value: float = 0.0
    title: str = "Tornado Chart"


@router.post("/candlestick", summary="K线图SVG")
async def candlestick(req: CandlestickRequest):
    try:
        svg = _renderer.candlestick(req.data, title=req.title)
        return {"svg": svg, "symbol": req.symbol, "data_points": len(req.data)}
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="candlestick failed", detail=str(e))


@router.post("/heatmap", summary="热力图SVG")
async def heatmap(req: HeatmapRequest):
    try:
        if not req.matrix or not req.matrix[0]:
            raise HTTPException(status_code=400, detail="矩阵数据不能为空")
        svg = _renderer.heatmap(req.matrix, req.row_labels, req.col_labels, title=req.title)
        return {"svg": svg}
    except HTTPException:
        raise
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="heatmap failed", detail=str(e))


@router.post("/waterfall", summary="瀑布图SVG")
async def waterfall(req: WaterfallRequest):
    try:
        svg = _renderer.waterfall(req.categories, req.values, title=req.title)
        return {"svg": svg}
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="waterfall failed", detail=str(e))


@router.post("/sensitivity", summary="敏感性龙卷风图SVG")
async def sensitivity_chart(req: SensitivityChartRequest):
    try:
        if not req.factors:
            raise HTTPException(status_code=400, detail="因子列表不能为空")
        sensitivities = {}
        for i, factor in enumerate(req.factors):
            low = req.low_values[i] if i < len(req.low_values) else req.base_value
            high = req.high_values[i] if i < len(req.high_values) else req.base_value
            sensitivities[factor] = [low, high]
        svg = _renderer.sensitivity_tornado(req.base_value, sensitivities, title=req.title)
        return {"svg": svg}
    except HTTPException:
        raise
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="sensitivity_chart failed", detail=str(e))
