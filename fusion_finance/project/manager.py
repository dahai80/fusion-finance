from __future__ import annotations

import fcntl
import json
import logging
import re
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import PROJECT_DIR
from ..exceptions import FinanceError
from ..utils.safe_path import safe_join

logger = logging.getLogger(__name__)

_PROJECT_ID_RE = re.compile(r"^proj_[0-9a-f]{8}$")
_MAX_VERSIONS = 200
_VERSIONS_SUBDIR = "versions"


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
    version: int = 0


class ProjectManager:
    def __init__(self, data_dir: str = ""):
        self.data_dir = Path(data_dir) if data_dir else PROJECT_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / ".trash").mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Project] = {}

    def _project_path(self, project_id: str) -> Path | None:
        if not project_id or not _PROJECT_ID_RE.match(project_id):
            logger.warning("invalid project_id rejected: %r", project_id)
            return None
        path = safe_join(self.data_dir, project_id, suffix=".json")
        if path is None:
            logger.warning("path traversal blocked for project_id: %r", project_id)
            return None
        return path

    def _versions_dir(self, project_id: str) -> Path:
        path = self._project_path(project_id)
        if path is None:
            raise FinanceError(message="invalid project id", detail=project_id)
        vdir = path.parent / project_id / _VERSIONS_SUBDIR
        vdir.mkdir(parents=True, exist_ok=True)
        return vdir

    def _version_data_path(self, project_id: str, version_num: int) -> Path:
        return self._versions_dir(project_id) / f"v{version_num}.json"

    def _lock_path(self, project_id: str) -> Path:
        return self.data_dir / f".{project_id}.lock"

    def _load_project(self, project_id: str) -> Project | None:
        if project_id in self._cache:
            return self._cache[project_id]
        path = self._project_path(project_id)
        if path is None or not path.exists():
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
                version=raw.get("version", 0),
            )
            self._cache[project_id] = proj
            return proj
        except Exception as e:
            logger.error("Failed to load project %s: %s", project_id, e)
            return None

    def _save_project(self, project: Project) -> None:
        path = self._project_path(project.id)
        if path is None:
            logger.error("cannot save project, invalid id: %s", project.id)
            return
        data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "metadata": project.metadata,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "current_data": project.current_data,
            "versions": project.versions,
            "version": project.version,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._cache[project.id] = project
        logger.info("Saved project: %s (version=%d)", project.id, project.version)

    def _with_lock(self, project_id: str, fn):
        lock_path = self._lock_path(project_id)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                return fn()
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)

    def _check_expected_version(self, project_id: str, expected_version: int) -> Project | None:
        proj = self._load_project(project_id)
        if not proj:
            return None
        if expected_version and proj.version != expected_version:
            raise FinanceError(
                message="project version conflict",
                detail=f"expected {expected_version} got {proj.version}",
            )
        return proj

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
            version=1,
        )

        def _do_create():
            self._save_project(proj)
            return proj

        result = self._with_lock(project_id, _do_create)
        logger.info("Created project: id=%s, name=%s", project_id, name)
        return result

    def get(self, project_id: str) -> Project | None:
        return self._load_project(project_id)

    def update(
        self,
        project_id: str,
        name: str = "",
        description: str = "",
        metadata: dict | None = None,
        data: dict | None = None,
        expected_version: int = 0,
    ) -> Project | None:

        def _do_update():
            proj = self._check_expected_version(project_id, expected_version)
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
            proj.version += 1
            self._cache[project_id] = proj
            self._save_project(proj)
            logger.info("Updated project: %s (version=%d)", project_id, proj.version)
            return proj

        try:
            return self._with_lock(project_id, _do_update)
        except FinanceError:
            raise
        except Exception as e:
            logger.error("update project failed: %s", e)
            return None

    def delete(self, project_id: str) -> bool:
        path = self._project_path(project_id)
        if path is None or not path.exists():
            logger.warning("Project not found for delete: %s", project_id)
            return False

        def _do_delete():
            trash_dir = self.data_dir / ".trash"
            trash_dir.mkdir(parents=True, exist_ok=True)
            trash_path = trash_dir / f"{project_id}.json"
            try:
                shutil.copy2(str(path), str(trash_path))
                logger.info("Backed up project %s to trash: %s", project_id, trash_path)
            except OSError as e:
                logger.warning("trash backup failed for %s: %s", project_id, e)
            vdir = path.parent / project_id
            if vdir.exists():
                try:
                    trash_vdir = trash_dir / project_id
                    if trash_vdir.exists():
                        shutil.rmtree(trash_vdir)
                    shutil.copytree(str(vdir), str(trash_vdir))
                except OSError as e:
                    logger.warning("trash version backup failed for %s: %s", project_id, e)
            path.unlink()
            self._cache.pop(project_id, None)
            logger.info("Deleted project: %s", project_id)
            return True

        return self._with_lock(project_id, _do_delete)

    def list_projects(self) -> list[dict[str, Any]]:
        result = []
        for f in self.data_dir.glob("proj_*.json"):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                result.append(
                    {
                        "id": raw.get("id", ""),
                        "name": raw.get("name", ""),
                        "description": raw.get("description", ""),
                        "created_at": raw.get("created_at", 0),
                        "updated_at": raw.get("updated_at", 0),
                        "version_count": len(raw.get("versions", [])),
                    }
                )
            except Exception as e:
                logger.warning("Failed to read project file %s: %s", f.name, e)
        result.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return result

    def _write_version_data(self, project_id: str, version_num: int, data: dict[str, Any]) -> str:
        vpath = self._version_data_path(project_id, version_num)
        vpath.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return vpath.name

    def _read_version_data(self, project_id: str, version_num: int) -> dict[str, Any]:
        vpath = self._version_data_path(project_id, version_num)
        if not vpath.exists():
            logger.warning("version data file missing: %s", vpath)
            return {}
        try:
            return json.loads(vpath.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read version data %s: %s", vpath, e)
            return {}

    def _evict_oldest_versions(self, proj: Project) -> None:
        if len(proj.versions) <= _MAX_VERSIONS:
            return
        excess = len(proj.versions) - _MAX_VERSIONS
        evicted = proj.versions[:excess]
        proj.versions = proj.versions[excess:]
        for v in evicted:
            vnum = v.get("version", 0)
            if vnum <= 0:
                continue
            vpath = self._version_data_path(proj.id, vnum)
            try:
                if vpath.exists():
                    vpath.unlink()
            except OSError as e:
                logger.warning("Failed to evict version data %s: %s", vpath, e)
        logger.info("Evicted %d oldest versions for project %s", excess, proj.id)

    def snapshot(
        self, project_id: str, label: str = "", data: dict | None = None, expected_version: int = 0
    ) -> dict | None:

        def _do_snapshot():
            proj = self._check_expected_version(project_id, expected_version)
            if not proj:
                logger.warning("Project not found for snapshot: %s", project_id)
                return None
            version_num = len(proj.versions) + 1
            snapshot_data = data if data is not None else proj.current_data
            data_file = self._write_version_data(project_id, version_num, snapshot_data)
            snap = {
                "version": version_num,
                "label": label or f"v{version_num}",
                "data_file": data_file,
                "timestamp": time.time(),
            }
            proj.versions.append(snap)
            proj.current_data = snapshot_data
            proj.updated_at = time.time()
            proj.version += 1
            self._evict_oldest_versions(proj)
            self._cache[project_id] = proj
            self._save_project(proj)
            logger.info("Saved snapshot: project=%s, version=%d", project_id, version_num)
            return {"project_id": project_id, "version": version_num, "label": snap["label"]}

        try:
            return self._with_lock(project_id, _do_snapshot)
        except FinanceError:
            raise
        except Exception as e:
            logger.error("snapshot failed: %s", e)
            return None

    def restore(self, project_id: str, version: int | None = None) -> dict | None:

        def _do_restore():
            proj = self._load_project(project_id)
            if not proj:
                logger.warning("Project not found for restore: %s", project_id)
                return None
            if not proj.versions:
                logger.warning("No versions to restore for project: %s", project_id)
                return None
            if version is None or version <= 0:
                target = proj.versions[-1]
                target_ver = target["version"]
                logger.info("restore: version unset, using latest version %d", target_ver)
            else:
                target_ver = version
                target = None
                for v in proj.versions:
                    if v["version"] == target_ver:
                        target = v
                        break
            if not target:
                logger.warning("Version %d not found for project: %s", target_ver, project_id)
                return None
            target_data = self._read_version_data(project_id, target_ver)
            proj.current_data = target_data
            proj.updated_at = time.time()
            proj.version += 1
            self._cache[project_id] = proj
            self._save_project(proj)
            logger.info("Restored project %s to version %d", project_id, target_ver)
            return {"project_id": project_id, "restored_version": target_ver, "label": target["label"]}

        try:
            return self._with_lock(project_id, _do_restore)
        except FinanceError:
            raise
        except Exception as e:
            logger.error("restore failed: %s", e)
            return None

    def get_versions(self, project_id: str) -> list[dict[str, Any]]:
        proj = self._load_project(project_id)
        if not proj:
            return []
        return [{"version": v["version"], "label": v["label"], "timestamp": v["timestamp"]} for v in proj.versions]

    def get_version_data(self, project_id: str, version: int) -> dict[str, Any]:
        return self._read_version_data(project_id, version)
