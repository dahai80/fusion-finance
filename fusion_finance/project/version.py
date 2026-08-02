from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class VersionControl:
    def __init__(self):
        self._diff_cache: dict[str, str] = {}

    @staticmethod
    def compute_hash(data: Any) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def diff(self, old_data: dict[str, Any], new_data: dict[str, Any]) -> dict[str, Any]:
        added = {}
        removed = {}
        changed = {}
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))
        for key in all_keys:
            in_old = key in old_data
            in_new = key in new_data
            if in_old and not in_new:
                removed[key] = old_data[key]
            elif not in_old and in_new:
                added[key] = new_data[key]
            elif old_data[key] != new_data[key]:
                changed[key] = {"old": old_data[key], "new": new_data[key]}
        result = {
            "added": added,
            "removed": removed,
            "changed": changed,
            "old_hash": self.compute_hash(old_data),
            "new_hash": self.compute_hash(new_data),
        }
        logger.debug("Diff computed: +%d -%d ~%d keys", len(added), len(removed), len(changed))
        return result

    def patch(self, base_data: dict[str, Any], diff_result: dict[str, Any]) -> dict[str, Any]:
        result = dict(base_data)
        for key in diff_result.get("removed", {}):
            result.pop(key, None)
        for key, val in diff_result.get("added", {}).items():
            result[key] = val
        for key, change in diff_result.get("changed", {}).items():
            result[key] = change["new"]
        logger.debug("Patch applied: base_hash=%s", self.compute_hash(base_data))
        return result

    def cherry_pick(self, versions: list[dict[str, Any]], target_version: int) -> dict[str, Any] | None:
        for v in versions:
            if v.get("version") == target_version:
                return v.get("data", {})
        logger.warning("Version %d not found for cherry-pick", target_version)
        return None

    def history_summary(self, versions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summary = []
        for i, v in enumerate(versions):
            entry = {
                "version": v.get("version", i + 1),
                "label": v.get("label", f"v{i + 1}"),
                "timestamp": v.get("timestamp", 0),
                "data_hash": self.compute_hash(v.get("data", {})),
            }
            if i > 0:
                prev_data = versions[i - 1].get("data", {})
                cur_data = v.get("data", {})
                d = self.diff(prev_data, cur_data)
                entry["changes"] = {
                    "added": len(d["added"]),
                    "removed": len(d["removed"]),
                    "changed": len(d["changed"]),
                }
            summary.append(entry)
        return summary
