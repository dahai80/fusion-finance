from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...config import EXPORT_DIR, MAX_LIST_LENGTH
from ...exceptions import DataError, FinanceError, ReportError
from ...modeling.engine import CompsAnalysis, DCFModel
from ...report.formatter import SUPPORTED_FORMATS, ReportFormatter
from ...report.reports import ReportGenerator
from ...utils.safe_path import safe_join, sanitize_name
from ..dependencies import get_mlx_client

logger = logging.getLogger(__name__)

router = APIRouter()
_formatter = ReportFormatter()


class ValuationReportRequest(BaseModel):
    company: str
    revenue: list[float] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)
    ebit_margin: list[float] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    include_comps: bool = False
    peers: list[dict[str, float]] | None = Field(default=None, max_length=MAX_LIST_LENGTH)


class PitchbookRequest(BaseModel):
    company: str
    industry: str
    revenue: list[float] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)
    ebit_margin: list[float] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0


class ResearchReportRequest(BaseModel):
    company: str
    industry: str
    data: dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    content: str = ""
    template_name: str = ""
    template_data: dict[str, Any] | None = None
    name: str = ""


def _build_dcf_from_req(req) -> DCFModel:
    return DCFModel(
        company=req.company,
        forecast_years=len(req.revenue) if req.revenue else 5,
        revenue=req.revenue,
        ebit_margin=req.ebit_margin,
        tax_rate=req.tax_rate,
        wacc=req.wacc,
        terminal_growth=req.terminal_growth,
        net_debt=req.net_debt,
        shares_outstanding=req.shares_outstanding,
    )


@router.post("/valuation", summary="生成估值报告")
async def generate_valuation_report(req: ValuationReportRequest):
    try:
        dcf = _build_dcf_from_req(req)
        dcf.calculate()
        comps = None
        if req.include_comps and req.peers:
            comps = CompsAnalysis(company=req.company, peers=req.peers)
        generator = ReportGenerator()
        content = generator.generate_valuation_report(req.company, dcf, comps)
        return {"company": req.company, "content": content, "format": "markdown"}
    except ReportError:
        raise
    except FinanceError:
        raise
    except Exception as e:
        logger.error("generate_valuation_report failed: %s", e)
        raise ReportError(
            message="generate_valuation_report failed", detail=str(e), report_type="generate_valuation_report"
        )


@router.post("/pitchbook", summary="生成PitchBook")
async def generate_pitchbook(req: PitchbookRequest):
    try:
        dcf = _build_dcf_from_req(req)
        dcf.calculate()
        generator = ReportGenerator()
        content = generator.generate_pitchbook(req.company, dcf, req.industry)
        return {"company": req.company, "content": content, "format": "markdown"}
    except ReportError:
        raise
    except FinanceError:
        raise
    except Exception as e:
        logger.error("generate_pitchbook failed: %s", e)
        raise ReportError(message="generate_pitchbook failed", detail=str(e), report_type="generate_pitchbook")


@router.post("/research", summary="AI生成深度投研报告")
async def generate_research_report(req: ResearchReportRequest, mlx=Depends(get_mlx_client)):
    try:
        generator = ReportGenerator(mlx)
        content = await generator.generate_research_report(req.company, req.industry, req.data)
        return {"company": req.company, "content": content, "format": "markdown"}
    except ReportError:
        raise
    except FinanceError:
        raise
    except Exception as e:
        logger.error("generate_research_report failed: %s", e)
        raise ReportError(
            message="generate_research_report failed", detail=str(e), report_type="generate_research_report"
        )


@router.post("/export/{fmt}", summary="导出报告")
async def export_report(fmt: str, req: ExportRequest):
    fmt_lower = fmt.lower()
    if fmt_lower not in SUPPORTED_FORMATS:
        logger.warning("export_report rejected unsupported format: %s", fmt)
        raise HTTPException(status_code=400, detail="unsupported format")
    ext = fmt_lower if fmt_lower != "md" else "md"
    safe_name = sanitize_name(req.name, fallback=f"report.{ext}")
    if not safe_name.endswith(f".{ext}"):
        safe_name = f"{safe_name}.{ext}"
    target = safe_join(EXPORT_DIR, safe_name)
    if target is None:
        logger.warning("export_report rejected unsafe name: %s", req.name)
        raise DataError(message="unsafe export name", detail="invalid name", field="name")
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = _formatter.export(
            content=req.content,
            fmt=fmt_lower,
            output_path=str(target),
            template_name=req.template_name,
            template_data=req.template_data,
        )
        actual_ext = str(path).rsplit(".", 1)[-1].lower() if "." in str(path) else fmt_lower
        actual_format = "markdown" if actual_ext == "md" else actual_ext
        degraded = actual_format != fmt_lower
        if degraded:
            logger.warning("export_report degraded: requested %s but wrote %s at %s", fmt_lower, actual_format, path)
        return {
            "format": actual_format,
            "requested_format": fmt_lower,
            "degraded": degraded,
            "path": path,
            "status": "ok",
        }
    except ValueError as e:
        logger.warning("export_report value error: %s", e)
        raise HTTPException(status_code=400, detail="invalid export request")
    except ReportError:
        raise
    except FinanceError:
        raise
    except Exception as e:
        logger.error("export_report failed: %s", e)
        raise ReportError(message="export_report failed", detail=str(e), report_type="export_report")


@router.get("/formats", summary="支持的导出格式")
async def list_formats():
    return {"formats": list(SUPPORTED_FORMATS)}
