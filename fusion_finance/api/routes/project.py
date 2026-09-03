from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config import EXPORT_DIR
from ...exceptions import DataError, FinanceError
from ...project import ProjectExporter, ProjectManager, VersionControl
from ...utils.safe_path import safe_join, sanitize_name

logger = logging.getLogger(__name__)

router = APIRouter()

_manager = ProjectManager()
_vc = VersionControl()
_exporter = ProjectExporter(manager=_manager)


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    metadata: dict[str, Any] | None = None


class ProjectUpdateRequest(BaseModel):
    name: str = ""
    description: str = ""
    metadata: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


class SnapshotRequest(BaseModel):
    label: str = ""
    data: dict[str, Any] | None = None


class RestoreRequest(BaseModel):
    version: int = 0


class ExportRequest(BaseModel):
    format: str = "json"
    name: str = ""


@router.get("/list", summary="列出所有项目")
async def list_projects():
    try:
        projects = _manager.list_projects()
        return {"projects": projects, "total": len(projects)}
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="list_projects failed", detail=str(e))


@router.post("/create", summary="创建项目")
async def create_project(req: ProjectCreateRequest):
    try:
        proj = _manager.create(name=req.name, description=req.description, metadata=req.metadata)
        return {"id": proj.id, "name": proj.name, "created_at": proj.created_at}
    except FinanceError:
        raise
    except Exception as e:
        raise FinanceError(message="create_project failed", detail=str(e))


@router.get("/{project_id}", summary="获取项目详情")
async def get_project(project_id: str):
    proj = _manager.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "id": proj.id,
        "name": proj.name,
        "description": proj.description,
        "metadata": proj.metadata,
        "created_at": proj.created_at,
        "updated_at": proj.updated_at,
        "current_data": proj.current_data,
        "version_count": len(proj.versions),
    }


@router.put("/{project_id}", summary="更新项目")
async def update_project(project_id: str, req: ProjectUpdateRequest):
    try:
        proj = _manager.update(
            project_id, name=req.name, description=req.description, metadata=req.metadata, data=req.data
        )
    except DataError as e:
        if e.field == "project_id" and e.message == "project not found":
            raise HTTPException(status_code=404, detail="项目不存在")
        raise
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"id": proj.id, "name": proj.name, "updated_at": proj.updated_at}


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(project_id: str):
    ok = _manager.delete(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"id": project_id, "deleted": True}


@router.post("/{project_id}/snapshot", summary="保存快照")
async def save_snapshot(project_id: str, req: SnapshotRequest):
    try:
        result = _manager.snapshot(project_id, label=req.label, data=req.data)
    except DataError as e:
        if e.message == "project not found":
            raise HTTPException(status_code=404, detail="项目不存在")
        raise
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result


@router.get("/{project_id}/versions", summary="版本历史")
async def get_versions(project_id: str):
    versions = _manager.get_versions(project_id)
    return {"project_id": project_id, "versions": versions, "total": len(versions)}


@router.post("/{project_id}/restore", summary="恢复版本")
async def restore_version(project_id: str, req: RestoreRequest):
    try:
        result = _manager.restore(project_id, version=req.version)
    except DataError as e:
        if e.message in ("project not found", "version not found", "no versions to restore"):
            raise HTTPException(status_code=404, detail="项目或版本不存在")
        raise
    if not result:
        raise HTTPException(status_code=404, detail="项目或版本不存在")
    return result


@router.get("/{project_id}/diff", summary="版本差异对比")
async def diff_versions(project_id: str, v1: int = 0, v2: int = 0):
    proj = _manager.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    versions = proj.versions
    if len(versions) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个版本才能对比")
    idx1 = v1 - 1 if v1 > 0 else len(versions) - 2
    idx2 = v2 - 1 if v2 > 0 else len(versions) - 1
    if idx1 < 0 or idx1 >= len(versions) or idx2 < 0 or idx2 >= len(versions):
        raise HTTPException(status_code=400, detail="版本号超出范围")
    diff_result = _vc.diff(versions[idx1].get("data", {}), versions[idx2].get("data", {}))
    return {"project_id": project_id, "v1": idx1 + 1, "v2": idx2 + 1, "diff": diff_result}


@router.get("/{project_id}/history", summary="版本变更摘要")
async def version_history(project_id: str):
    proj = _manager.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    summary = _vc.history_summary(proj.versions)
    return {"project_id": project_id, "history": summary}


@router.post("/{project_id}/export", summary="导出项目")
async def export_project(project_id: str, req: ExportRequest):
    fmt = req.format.lower()
    ext = "zip" if fmt == "zip" else "json"
    safe_name = sanitize_name(req.name, fallback=f"{project_id}.{ext}")
    if not safe_name.endswith(f".{ext}"):
        safe_name = f"{safe_name}.{ext}"
    target = safe_join(EXPORT_DIR, safe_name)
    if target is None:
        logger.warning("export_project rejected unsafe name: %s", req.name)
        raise DataError(message="unsafe export name", detail="invalid name", field="name")
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        if fmt == "zip":
            path = _exporter.export_zip(project_id, str(target))
        else:
            path = _exporter.export_json(project_id, str(target))
        if not path:
            raise HTTPException(status_code=404, detail="项目不存在或导出失败")
        return {"project_id": project_id, "format": fmt, "path": path}
    except HTTPException:
        raise
    except DataError:
        raise
    except FinanceError:
        raise
    except Exception as e:
        logger.error("export_project failed: %s", e)
        raise FinanceError(message="export_project failed", detail=str(e))
