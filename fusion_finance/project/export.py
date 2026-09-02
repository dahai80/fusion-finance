from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import EXPORT_DIR
from ..utils.safe_path import safe_join, sanitize_name
from .manager import Project, ProjectManager

logger = logging.getLogger(__name__)


class ProjectExporter:
    def __init__(self, manager: ProjectManager | None = None):
        self.manager = manager or ProjectManager()
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def export_json(self, project_id: str, output_path: str = "") -> str | None:
        proj = self.manager.get(project_id)
        if not proj:
            logger.warning("Project not found for export: %s", project_id)
            return None
        base = output_path or f"{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = sanitize_name(base, fallback=f"{project_id}_export")
        path = safe_join(EXPORT_DIR, name, suffix=".json")
        if path is None:
            logger.error("export_json: unsafe output name rejected: %r", base)
            return None
        data = self._project_to_dict(proj)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        logger.info("Exported project %s to JSON: %s", project_id, path)
        return str(path)

    def export_zip(self, project_id: str, output_path: str = "") -> str | None:
        proj = self.manager.get(project_id)
        if not proj:
            logger.warning("Project not found for export: %s", project_id)
            return None
        base = output_path or f"{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = sanitize_name(base, fallback=f"{project_id}_export")
        path = safe_join(EXPORT_DIR, name, suffix=".zip")
        if path is None:
            logger.error("export_zip: unsafe output name rejected: %r", base)
            return None
        try:
            with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
                data = self._project_to_dict(proj)
                zf.writestr("project.json", json.dumps(data, ensure_ascii=False, indent=2, default=str))
                for i, v in enumerate(proj.versions):
                    version_json = json.dumps(v, ensure_ascii=False, indent=2, default=str)
                    zf.writestr(f"versions/v{v.get('version', i + 1)}.json", version_json)
                if proj.current_data:
                    zf.writestr(
                        "current_data.json", json.dumps(proj.current_data, ensure_ascii=False, indent=2, default=str)
                    )
            logger.info("Exported project %s to ZIP: %s", project_id, path)
            return str(path)
        except Exception as e:
            logger.error("ZIP export failed for %s: %s", project_id, e)
            return None

    def import_json(self, input_path: str) -> str | None:
        resolved = self._resolve_import_path(input_path, suffix=".json")
        if resolved is None:
            return None
        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
            name = data.get("name", resolved.stem)
            description = data.get("description", f"Imported from {resolved.name}")
            proj = self.manager.create(name=name, description=description, metadata=data.get("metadata", {}))
            if data.get("current_data"):
                self.manager.update(proj.id, data=data["current_data"])
            for v in data.get("versions", []):
                self.manager.snapshot(proj.id, label=v.get("label", ""), data=v.get("data", {}))
            logger.info("Imported project from %s: id=%s", resolved, proj.id)
            return proj.id
        except Exception as e:
            logger.error("Import failed for %s: %s", resolved, e)
            return None

    def import_zip(self, input_path: str) -> str | None:
        resolved = self._resolve_import_path(input_path, suffix=".zip")
        if resolved is None:
            return None
        try:
            with zipfile.ZipFile(str(resolved), "r") as zf:
                if "project.json" not in zf.namelist():
                    logger.error("Invalid project ZIP: missing project.json")
                    return None
                data = json.loads(zf.read("project.json"))
                name = data.get("name", resolved.stem)
                description = data.get("description", f"Imported from {resolved.name}")
                proj = self.manager.create(name=name, description=description, metadata=data.get("metadata", {}))
                if "current_data.json" in zf.namelist():
                    cur = json.loads(zf.read("current_data.json"))
                    self.manager.update(proj.id, data=cur)
                version_files = sorted([f for f in zf.namelist() if f.startswith("versions/") and f.endswith(".json")])
                for vf in version_files:
                    vdata = json.loads(zf.read(vf))
                    self.manager.snapshot(proj.id, label=vdata.get("label", ""), data=vdata.get("data", {}))
                logger.info("Imported project from ZIP %s: id=%s", resolved, proj.id)
                return proj.id
        except Exception as e:
            logger.error("ZIP import failed for %s: %s", resolved, e)
            return None

    @staticmethod
    def _resolve_import_path(input_path: str, suffix: str) -> Path | None:
        if not input_path:
            logger.error("import: empty input path")
            return None
        p = Path(input_path)
        if p.is_absolute() or ".." in p.parts:
            logger.error("import: reject absolute/relative-traversal path: %r", input_path)
            return None
        name = sanitize_name(input_path, fallback="")
        if not name:
            logger.error("import: reject unsafe path: %r", input_path)
            return None
        resolved = safe_join(EXPORT_DIR, name, suffix=suffix)
        if resolved is None or not resolved.exists():
            logger.error("import: path not in EXPORT_DIR or missing: %r", input_path)
            return None
        return resolved

    @staticmethod
    def _project_to_dict(proj: Project) -> dict[str, Any]:
        return {
            "id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "metadata": proj.metadata,
            "created_at": proj.created_at,
            "updated_at": proj.updated_at,
            "current_data": proj.current_data,
            "versions": proj.versions,
        }
