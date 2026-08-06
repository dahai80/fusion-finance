from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...ai_client import MLXClient
from ...exceptions import ReportError
from ...modeling.engine import CompsAnalysis, DCFModel
from ...report.formatter import SUPPORTED_FORMATS, ReportFormatter
from ...report.reports import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter()
_formatter = ReportFormatter()


class ValuationReportRequest(BaseModel):
    company: str
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.03
    net_debt: float = 0.0
    shares_outstanding: float = 0.0
    include_comps: bool = False
    peers: list[dict[str, float]] | None = None


class PitchbookRequest(BaseModel):
    company: str
    industry: str
    revenue: list[float] = Field(default_factory=list)
    ebit_margin: list[float] = Field(default_factory=list)
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
    output_path: str = ""


def _get_mlx() -> MLXClient:
    return MLXClient()


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
    except Exception as e:
        raise ReportError(
            message="generate_valuation_report failed", detail=str(e), risk_type="generate_valuation_report"
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
    except Exception as e:
        raise ReportError(message="generate_pitchbook failed", detail=str(e), risk_type="generate_pitchbook")


@router.post("/research", summary="AI生成深度投研报告")
async def generate_research_report(req: ResearchReportRequest):
    try:
        generator = ReportGenerator(_get_mlx())
        content = await generator.generate_research_report(req.company, req.industry, req.data)
        return {"company": req.company, "content": content, "format": "markdown"}
    except ReportError:
        raise
    except Exception as e:
        raise ReportError(
            message="generate_research_report failed", detail=str(e), risk_type="generate_research_report"
        )


@router.post("/export/{fmt}", summary="导出报告")
async def export_report(fmt: str, req: ExportRequest):
    try:
        path = _formatter.export(
            content=req.content,
            fmt=fmt,
            output_path=req.output_path,
            template_name=req.template_name,
            template_data=req.template_data,
        )
        return {"format": fmt, "path": path, "status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReportError:
        raise
    except Exception as e:
        raise ReportError(message="export_report failed", detail=str(e), risk_type="export_report")


@router.get("/formats", summary="支持的导出格式")
async def list_formats():
    return {"formats": list(SUPPORTED_FORMATS)}
