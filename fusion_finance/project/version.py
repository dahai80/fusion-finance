from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_REMOVED = "__removed__"


class VersionControl:
    def __init__(self):
        self._diff_cache: dict[str, str] = {}

    @staticmethod
    def compute_hash(data: Any) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _diff_values(old_val: Any, new_val: Any, path: str, changed: dict[str, Any]) -> None:
        if old_val == new_val:
            return
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            VersionControl._diff_dicts(old_val, new_val, path, changed)
        elif isinstance(old_val, list) and isinstance(new_val, list):
            VersionControl._diff_lists(old_val, new_val, path, changed)
        else:
            changed[path] = {"old": old_val, "new": new_val}

    @staticmethod
    def _diff_lists(old_list: list[Any], new_list: list[Any], path: str, changed: dict[str, Any]) -> None:
        max_len = max(len(old_list), len(new_list))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(old_list):
                changed[child_path] = {"old": _REMOVED, "new": new_list[i]}
            elif i >= len(new_list):
                changed[child_path] = {"old": old_list[i], "new": _REMOVED}
            else:
                VersionControl._diff_values(old_list[i], new_list[i], child_path, changed)

    @staticmethod
    def _diff_dicts(old_data: dict[str, Any], new_data: dict[str, Any], path: str, changed: dict[str, Any]) -> None:
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))
        for key in all_keys:
            child_path = f"{path}.{key}" if path else key
            in_old = key in old_data
            in_new = key in new_data
            if in_old and not in_new:
                changed[child_path] = {"old": old_data[key], "new": _REMOVED}
            elif not in_old and in_new:
                changed[child_path] = {"old": _REMOVED, "new": new_data[key]}
            else:
                VersionControl._diff_values(old_data[key], new_data[key], child_path, changed)

    def diff(self, old_data: dict[str, Any], new_data: dict[str, Any]) -> dict[str, Any]:
        added: dict[str, Any] = {}
        removed: dict[str, Any] = {}
        changed: dict[str, Any] = {}
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))
        for key in all_keys:
            in_old = key in old_data
            in_new = key in new_data
            if in_old and not in_new:
                removed[key] = old_data[key]
            elif not in_old and in_new:
                added[key] = new_data[key]
            elif old_data[key] != new_data[key]:
                if isinstance(old_data[key], dict) and isinstance(new_data[key], dict):
                    self._diff_dicts(old_data[key], new_data[key], key, changed)
                elif isinstance(old_data[key], list) and isinstance(new_data[key], list):
                    self._diff_lists(old_data[key], new_data[key], key, changed)
                else:
                    changed[key] = {"old": old_data[key], "new": new_data[key]}
        result = {
            "added": added,
            "removed": removed,
            "changed": changed,
            "old_hash": self.compute_hash(old_data),
            "new_hash": self.compute_hash(new_data),
        }
        logger.debug("Diff computed: +%d -%d ~%d paths", len(added), len(removed), len(changed))
        return result

    def patch(self, base_data: dict[str, Any], diff_result: dict[str, Any]) -> dict[str, Any]:
        result = dict(base_data)
        for key, val in diff_result.get("added", {}).items():
            result[key] = val
        for key in diff_result.get("removed", {}):
            result.pop(key, None)
        for path, change in diff_result.get("changed", {}).items():
            new_val = change["new"]
            if new_val == _REMOVED:
                self._unset_path(result, path)
            else:
                self._set_path(result, path, new_val)
        logger.debug("Patch applied: base_hash=%s", self.compute_hash(base_data))
        return result

    @staticmethod
    def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
        tokens = VersionControl._tokenize(path)
        if not tokens:
            return
        cur = data
        for tok in tokens[:-1]:
            cur = VersionControl._descend(cur, tok)
            if cur is None:
                return
        last = tokens[-1]
        if isinstance(last, int):
            if isinstance(cur, list) and 0 <= last < len(cur):
                cur[last] = value
        else:
            if isinstance(cur, dict):
                cur[last] = value

    @staticmethod
    def _unset_path(data: dict[str, Any], path: str) -> None:
        tokens = VersionControl._tokenize(path)
        if not tokens:
            return
        cur = data
        for tok in tokens[:-1]:
            cur = VersionControl._descend(cur, tok)
            if cur is None:
                return
        last = tokens[-1]
        if isinstance(last, int):
            if isinstance(cur, list) and 0 <= last < len(cur):
                cur[last] = None
        else:
            if isinstance(cur, dict):
                cur.pop(last, None)

    @staticmethod
    def _descend(cur: Any, tok: Any) -> Any:
        if isinstance(tok, int):
            if isinstance(cur, list) and 0 <= tok < len(cur):
                return cur[tok]
            return None
        if isinstance(tok, str) and isinstance(cur, dict) and tok in cur:
            return cur[tok]
        return None

    @staticmethod
    def _tokenize(path: str) -> list[Any]:
        tokens: list[Any] = []
        i = 0
        buf = ""
        while i < len(path):
            ch = path[i]
            if ch == ".":
                if buf:
                    tokens.append(buf)
                    buf = ""
                i += 1
            elif ch == "[":
                if buf:
                    tokens.append(buf)
                    buf = ""
                j = path.find("]", i + 1)
                if j == -1:
                    break
                idx = path[i + 1 : j]
                try:
                    tokens.append(int(idx))
                except ValueError:
                    tokens.append(idx)
                i = j + 1
            else:
                buf += ch
                i += 1
        if buf:
            tokens.append(buf)
        return tokens

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
