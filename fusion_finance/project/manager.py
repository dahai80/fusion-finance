from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import PROJECT_DIR

logger = logging.getLogger(__name__)


@dataclass
class Project:
    id: str = ""
    name: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    current_data: dict[str, Any] = field(default_factory=dict)
    versions: list[dict[str, Any]] = field(default_factory=list)


class ProjectManager:
    def __init__(self, data_dir: str = ""):
        self.data_dir = Path(data_dir) if data_dir else PROJECT_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Project] = {}

    def _project_path(self, project_id: str) -> Path:
        return self.data_dir / f"{project_id}.json"

    def _load_project(self, project_id: str) -> Project | None:
        if project_id in self._cache:
            return self._cache[project_id]
        path = self._project_path(project_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            proj = Project(
                id=raw.get("id", project_id),
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                metadata=raw.get("metadata", {}),
                created_at=raw.get("created_at", 0),
                updated_at=raw.get("updated_at", 0),
                current_data=raw.get("current_data", {}),
                versions=raw.get("versions", []),
            )
            self._cache[project_id] = proj
            return proj
        except Exception as e:
            logger.error("Failed to load project %s: %s", project_id, e)
            return None

    def _save_project(self, project: Project) -> None:
        path = self._project_path(project.id)
        data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "metadata": project.metadata,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "current_data": project.current_data,
            "versions": project.versions,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._cache[project.id] = project
        logger.info("Saved project: %s", project.id)

    def create(self, name: str, description: str = "", metadata: dict | None = None) -> Project:
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        now = time.time()
        proj = Project(
            id=project_id,
            name=name,
            description=description,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._save_project(proj)
        logger.info("Created project: id=%s, name=%s", project_id, name)
        return proj

    def get(self, project_id: str) -> Project | None:
        return self._load_project(project_id)

    def update(self, project_id: str, name: str = "", description: str = "",
               metadata: dict | None = None, data: dict | None = None) -> Project | None:
        proj = self._load_project(project_id)
        if not proj:
            logger.warning("Project not found: %s", project_id)
            return None
        if name:
            proj.name = name
        if description:
            proj.description = description
        if metadata:
            proj.metadata.update(metadata)
        if data:
            proj.current_data = data
        proj.updated_at = time.time()
        self._save_project(proj)
        logger.info("Updated project: %s", project_id)
        return proj

    def delete(self, project_id: str) -> bool:
        path = self._project_path(project_id)
        if not path.exists():
            logger.warning("Project not found for delete: %s", project_id)
            return False
        path.unlink()
        self._cache.pop(project_id, None)
        logger.info("Deleted project: %s", project_id)
        return True

    def list_projects(self) -> list[dict[str, Any]]:
        result = []
        for f in self.data_dir.glob("proj_*.json"):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                result.append({
                    "id": raw.get("id", ""),
                    "name": raw.get("name", ""),
                    "description": raw.get("description", ""),
                    "created_at": raw.get("created_at", 0),
                    "updated_at": raw.get("updated_at", 0),
                    "version_count": len(raw.get("versions", [])),
                })
            except Exception as e:
                logger.warning("Failed to read project file %s: %s", f.name, e)
        result.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return result

    def snapshot(self, project_id: str, label: str = "", data: dict | None = None) -> dict | None:
        proj = self._load_project(project_id)
        if not proj:
            logger.warning("Project not found for snapshot: %s", project_id)
            return None
        version_num = len(proj.versions) + 1
        snapshot_data = data if data is not None else proj.current_data
        snap = {
            "version": version_num,
            "label": label or f"v{version_num}",
            "data": snapshot_data,
            "timestamp": time.time(),
        }
        proj.versions.append(snap)
        proj.current_data = snapshot_data
        proj.updated_at = time.time()
        self._save_project(proj)
        logger.info("Saved snapshot: project=%s, version=%d", project_id, version_num)
        return {"project_id": project_id, "version": version_num, "label": snap["label"]}

    def restore(self, project_id: str, version: int = 0) -> dict | None:
        proj = self._load_project(project_id)
        if not proj:
            logger.warning("Project not found for restore: %s", project_id)
            return None
        if not proj.versions:
            logger.warning("No versions to restore for project: %s", project_id)
            return None
        target_ver = version if version > 0 else len(proj.versions)
        target = None
        for v in proj.versions:
            if v["version"] == target_ver:
                target = v
                break
        if not target:
            logger.warning("Version %d not found for project: %s", target_ver, project_id)
            return None
        proj.current_data = target["data"]
        proj.updated_at = time.time()
        self._save_project(proj)
        logger.info("Restored project %s to version %d", project_id, target_ver)
        return {"project_id": project_id, "restored_version": target_ver, "label": target["label"]}

    def get_versions(self, project_id: str) -> list[dict[str, Any]]:
        proj = self._load_project(project_id)
        if not proj:
            return []
        return [
            {"version": v["version"], "label": v["label"], "timestamp": v["timestamp"]}
            for v in proj.versions
        ]
