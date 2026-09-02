from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ...config import CACHE_DIR, MAX_LIST_LENGTH, MAX_UPLOAD_BYTES
from ...data import DataAdapter
from ...data.market_feed import MarketDataAdapter
from ...exceptions import DataError
from ...utils.safe_path import safe_join, sanitize_name

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
    data: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)
    required_fields: list[str] | None = None


@router.post("/import", summary="导入CSV数据")
async def import_data(file: UploadFile = File(default=...)):
    try:
        content_type = file.content_type or ""
        if (
            content_type
            and "csv" not in content_type
            and "text" not in content_type
            and "octet-stream" not in content_type
        ):
            logger.warning("Import received non-csv content-type: %s", content_type)

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                logger.warning("Import rejected: upload exceeds %d bytes", MAX_UPLOAD_BYTES)
                raise HTTPException(status_code=413, detail="上传文件过大")
            chunks.append(chunk)
        content = b"".join(chunks)
        text = content.decode("utf-8-sig")

        result = _adapter.load_csv(text)

        raw_name = file.filename or "data.csv"
        safe_name = sanitize_name(raw_name, fallback="data.csv")
        if not safe_name.endswith(".csv"):
            safe_name = f"{safe_name}.csv"
        key = f"csv_{int(time.time())}_{safe_name}"

        target = safe_join(CACHE_DIR, f"{key}.json")
        if target is None:
            logger.warning("Import rejected unsafe filename: %s", raw_name)
            raise DataError(message="unsafe filename", detail="invalid filename", field="filename")

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result["data"], ensure_ascii=False), encoding="utf-8")

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
    except HTTPException:
        raise
    except UnicodeDecodeError:
        logger.warning("Import failed: non-utf8 encoding")
        raise HTTPException(status_code=400, detail="文件编码不支持，请使用UTF-8编码的CSV")
    except DataError:
        raise
    except Exception as e:
        logger.error("import_data failed: %s", e)
        raise DataError(message="import_data failed", detail=str(e), field="import_data")


@router.post("/validate/balance", summary="验证资产负债表平衡")
async def validate_balance(req: ValidateBalanceRequest):
    try:
        result = _adapter.validate_balance(req.assets, req.liabilities, req.equity, req.tolerance)
        return result
    except DataError:
        raise
    except Exception as e:
        logger.error("validate_balance failed: %s", e)
        raise DataError(message="validate_balance failed", detail=str(e), field="validate_balance")


@router.post("/validate/completeness", summary="数据完整性检查")
async def check_completeness(req: CompletenessRequest):
    try:
        result = _adapter.check_completeness(req.data, req.required_fields)
        return result
    except DataError:
        raise
    except Exception as e:
        logger.error("check_completeness failed: %s", e)
        raise DataError(message="check_completeness failed", detail=str(e), field="check_completeness")


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
    except DataError:
        raise
    except Exception as e:
        logger.error("list_cache failed: %s", e)
        raise DataError(message="list_cache failed", detail=str(e), field="list_cache")


@router.delete("/cache/{key}", summary="删除缓存项")
async def delete_cache(key: str):
    try:
        if "/" in key or "\\" in key or ".." in key or not key:
            logger.warning("delete_cache rejected unsafe key: %s", key)
            raise HTTPException(status_code=400, detail="非法缓存键")
        target = safe_join(CACHE_DIR, f"{key}.json")
        if target is None or not target.exists():
            raise HTTPException(status_code=404, detail="缓存项不存在")
        target.unlink()
        logger.info("Deleted cache: %s", key)
        return {"deleted": key}
    except HTTPException:
        raise
    except DataError:
        raise
    except Exception as e:
        logger.error("delete_cache failed: %s", e)
        raise DataError(message="delete_cache failed", detail=str(e), field="delete_cache")


class MarketQuoteRequest(BaseModel):
    market: str = "A"


class OHLCVRequest(BaseModel):
    symbol: str = "600519"
    base_price: float = 100.0
    bars: int = 60


class TechnicalsRequest(BaseModel):
    ohlcv: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)


@router.get("/market/quotes", summary="获取模拟行情报价")
async def market_quotes(market: str = "A"):
    try:
        quotes = _market.get_quotes(market)
        return {"market": market, "quotes": quotes, "count": len(quotes)}
    except DataError:
        raise
    except Exception as e:
        logger.error("market_quotes failed: %s", e)
        raise DataError(message="market_quotes failed", detail=str(e), field="market_quotes")


@router.post("/market/ohlcv", summary="获取模拟OHLCV数据")
async def market_ohlcv(req: OHLCVRequest):
    try:
        ohlcv = _market.get_ohlcv(req.symbol, req.base_price, req.bars)
        return {"symbol": req.symbol, "ohlcv": ohlcv, "count": len(ohlcv)}
    except DataError:
        raise
    except Exception as e:
        logger.error("market_ohlcv failed: %s", e)
        raise DataError(message="market_ohlcv failed", detail=str(e), field="market_ohlcv")


@router.post("/market/technicals", summary="计算技术指标")
async def market_technicals(req: TechnicalsRequest):
    try:
        result = _market.compute_technicals(req.ohlcv)
        return result
    except DataError:
        raise
    except Exception as e:
        logger.error("market_technicals failed: %s", e)
        raise DataError(message="market_technicals failed", detail=str(e), field="market_technicals")
