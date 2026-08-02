from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ...config import CACHE_DIR
from ...data import DataAdapter
from ...data.market_feed import MarketDataAdapter

logger = logging.getLogger(__name__)

router = APIRouter()

_adapter = DataAdapter()
_market = MarketDataAdapter()


class ImportResponse(BaseModel):
    key: str
    rows: int = 0
    columns: list[str] = Field(default_factory=list)
    valid_rows: int = 0
    preview: list[dict[str, Any]] = Field(default_factory=list)


class ValidateBalanceRequest(BaseModel):
    assets: float
    liabilities: float
    equity: float
    tolerance: float = 0.01


class CompletenessRequest(BaseModel):
    data: list[dict[str, Any]] = Field(default_factory=list)
    required_fields: list[str] | None = None


@router.post("/import", summary="导入CSV数据")
async def import_data(file: UploadFile = File(default=...)):
    try:
        filename = file.filename or "data.csv"
        content = await file.read()
        text = content.decode("utf-8-sig")

        result = _adapter.load_csv(text)
        key = f"csv_{int(time.time())}_{filename}"

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data_path = CACHE_DIR / f"{key}.json"
        data_path.write_text(json.dumps(result["data"], ensure_ascii=False), encoding="utf-8")

        preview = result["data"][:10]
        columns = list(result["data"][0].keys()) if result["data"] else []
        logger.info("Imported CSV: key=%s, rows=%d, valid=%d", key, result["row_count"], result["valid_rows"])
        return ImportResponse(
            key=key,
            rows=result["row_count"],
            columns=columns,
            valid_rows=result["valid_rows"],
            preview=preview,
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码不支持，请使用UTF-8编码的CSV")
    except Exception as e:
        logger.error("import_data failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/balance", summary="验证资产负债表平衡")
async def validate_balance(req: ValidateBalanceRequest):
    try:
        result = _adapter.validate_balance(req.assets, req.liabilities, req.equity, req.tolerance)
        return result
    except Exception as e:
        logger.error("validate_balance failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/completeness", summary="数据完整性检查")
async def check_completeness(req: CompletenessRequest):
    try:
        result = _adapter.check_completeness(req.data, req.required_fields)
        return result
    except Exception as e:
        logger.error("check_completeness failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache", summary="列出缓存数据")
async def list_cache():
    try:
        items = []
        if CACHE_DIR.exists():
            for f in sorted(CACHE_DIR.glob("csv_*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    items.append(
                        {
                            "key": f.stem,
                            "rows": len(data) if isinstance(data, list) else 0,
                        }
                    )
                except Exception:
                    continue
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error("list_cache failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/{key}", summary="删除缓存项")
async def delete_cache(key: str):
    try:
        data_path = CACHE_DIR / f"{key}.json"
        if not data_path.exists():
            raise HTTPException(status_code=404, detail="缓存项不存在")
        data_path.unlink()
        logger.info("Deleted cache: %s", key)
        return {"deleted": key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_cache failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class MarketQuoteRequest(BaseModel):
    market: str = "A"


class OHLCVRequest(BaseModel):
    symbol: str = "600519"
    base_price: float = 100.0
    bars: int = 60


class TechnicalsRequest(BaseModel):
    ohlcv: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/market/quotes", summary="获取模拟行情报价")
async def market_quotes(market: str = "A"):
    try:
        quotes = _market.get_quotes(market)
        return {"market": market, "quotes": quotes, "count": len(quotes)}
    except Exception as e:
        logger.error("market_quotes failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/ohlcv", summary="获取模拟OHLCV数据")
async def market_ohlcv(req: OHLCVRequest):
    try:
        ohlcv = _market.get_ohlcv(req.symbol, req.base_price, req.bars)
        return {"symbol": req.symbol, "ohlcv": ohlcv, "count": len(ohlcv)}
    except Exception as e:
        logger.error("market_ohlcv failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/technicals", summary="计算技术指标")
async def market_technicals(req: TechnicalsRequest):
    try:
        result = _market.compute_technicals(req.ohlcv)
        return result
    except Exception as e:
        logger.error("market_technicals failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
