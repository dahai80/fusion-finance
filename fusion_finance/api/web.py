from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from .. import __version__
from ..config import get_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

_WEB_DIR = Path(__file__).resolve().parent / "web"
templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))

_PAGES = {
    "dashboard": ("Dashboard", "/ui"),
    "modeling": ("Modeling", "/ui/modeling"),
    "risk": ("Risk & Compliance", "/ui/risk"),
    "copilot": ("Copilot", "/ui/copilot"),
}


def _render(request: Request, page: str, template: str):
    title, path = _PAGES[page]
    api_key = get_api_key()
    # api_key is injected for first-party JS calls on the loopback-bound local UI;
    # auth_safety_check warns on any non-loopback bind
    logger.info("web page served: %s", page)
    return templates.TemplateResponse(
        request,
        template,
        {"page": page, "page_title": title, "pages": _PAGES, "api_key": api_key, "version": __version__},
    )


@router.get("/ui", summary="Web UI dashboard")
async def ui_dashboard(request: Request):
    return _render(request, "dashboard", "dashboard.html")


@router.get("/ui/modeling", summary="Web UI modeling")
async def ui_modeling(request: Request):
    return _render(request, "modeling", "modeling.html")


@router.get("/ui/risk", summary="Web UI risk and compliance")
async def ui_risk(request: Request):
    return _render(request, "risk", "risk.html")


@router.get("/ui/copilot", summary="Web UI copilot chat")
async def ui_copilot(request: Request):
    return _render(request, "copilot", "copilot.html")
