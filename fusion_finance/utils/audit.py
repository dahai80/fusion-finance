from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_AUDIT_SINGLETON: AuditTrail | None = None
_MAX_INMEMORY_ENTRIES = 5000
_MAX_FILE_STATS_LINES = 100000
_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_ROTATED_FILES = 3
_GENESIS_HASH = "0" * 64


@dataclass
class AuditEntry:
    timestamp: float = 0.0
    user: str = ""
    action: str = ""
    module: str = ""
    details: Any = None
    status: str = "success"
    duration_ms: float = 0.0
    prev_hash: str = ""
    cur_hash: str = ""


def get_audit_trail(log_path: str = "") -> AuditTrail:
    global _AUDIT_SINGLETON
    if _AUDIT_SINGLETON is None or log_path:
        _AUDIT_SINGLETON = AuditTrail(log_path)
    return _AUDIT_SINGLETON


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _compute_cur_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(_canonical_json(payload).encode("utf-8"))
    return h.hexdigest()


def _entry_payload(entry: AuditEntry) -> dict[str, Any]:
    return {
        "timestamp": entry.timestamp,
        "user": entry.user,
        "action": entry.action,
        "module": entry.module,
        "details": entry.details,
        "status": entry.status,
        "duration_ms": entry.duration_ms,
        "prev_hash": entry.prev_hash,
    }


class AuditTrail:
    def __init__(self, log_path: str = ""):
        self.log_path = log_path or str(Path.home() / ".fusion" / "finance" / "audit.jsonl")
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.log_path + ".lock"
        self._entries: list[AuditEntry] = []
        self._corrupted_count = 0

    def _read_last_hash(self) -> str:
        try:
            with open(self.log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size == 0:
                    return _GENESIS_HASH
                tail = min(size, 8192)
                f.seek(size - tail)
                data = f.read(tail).decode("utf-8", errors="replace")
        except FileNotFoundError:
            return _GENESIS_HASH
        except OSError as e:
            logger.warning("audit _read_last_hash read failed: %s", e)
            return _GENESIS_HASH
        last_hash = _GENESIS_HASH
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                last_hash = raw.get("cur_hash", _GENESIS_HASH) or _GENESIS_HASH
            except Exception:
                continue
        return last_hash

    def _maybe_rotate(self) -> None:
        try:
            if not os.path.exists(self.log_path):
                return
            if os.path.getsize(self.log_path) < _MAX_FILE_BYTES:
                return
        except OSError as e:
            logger.warning("audit rotate stat failed: %s", e)
            return
        base = self.log_path
        for i in range(_MAX_ROTATED_FILES, 0, -1):
            src = f"{base}.{i}" if i > 1 else f"{base}.1"
            dst = f"{base}.{i + 1}" if i < _MAX_ROTATED_FILES else f"{base}.{_MAX_ROTATED_FILES}"
            try:
                if os.path.exists(src):
                    if i < _MAX_ROTATED_FILES:
                        os.replace(src, dst)
                    else:
                        os.unlink(src)
            except OSError as e:
                logger.warning("audit rotate cleanup %s failed: %s", src, e)
        try:
            os.replace(base, f"{base}.1")
        except OSError as e:
            logger.warning("audit rotate move failed: %s", e)

    def record(
        self, user: str, action: str, module: str, details: Any = "", status: str = "success", duration_ms: float = 0.0
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            user=user,
            action=action,
            module=module,
            details=details,
            status=status,
            duration_ms=duration_ms,
            prev_hash="",
        )
        payload = _entry_payload(entry)
        try:
            with open(self._lock_path, "w") as lockf:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
                try:
                    prev_hash = self._read_last_hash()
                    entry.prev_hash = prev_hash
                    payload = _entry_payload(entry)
                    entry.cur_hash = _compute_cur_hash(prev_hash, payload)
                    self._maybe_rotate()
                    with open(self.log_path, "a") as f:
                        record = {**payload, "cur_hash": entry.cur_hash}
                        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                finally:
                    fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            logger.error("Failed to acquire audit lock: %s", e)
            entry.cur_hash = _compute_cur_hash("", payload)
        except Exception as e:
            logger.error("Failed to write audit entry: %s", e)
            entry.cur_hash = entry.cur_hash or _compute_cur_hash("", payload)
        self._entries.append(entry)
        if len(self._entries) > _MAX_INMEMORY_ENTRIES:
            self._entries = self._entries[-_MAX_INMEMORY_ENTRIES:]
        return entry

    def query(
        self,
        user: str = "",
        action: str = "",
        module: str = "",
        status: str = "",
        start_time: float = 0.0,
        end_time: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        return self.query_from_file(
            user=user,
            action=action,
            module=module,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def _matches(
        self,
        e: AuditEntry,
        user: str,
        action: str,
        module: str,
        status: str,
        start_time: float,
        end_time: float,
    ) -> bool:
        if user and e.user != user:
            return False
        if action and e.action != action:
            return False
        if module and e.module != module:
            return False
        if status and e.status != status:
            return False
        if start_time and e.timestamp < start_time:
            return False
        return not (end_time and e.timestamp > end_time)

    def _iter_file_entries(self, paths: list[str]):
        for path in paths:
            try:
                f = open(path)
            except FileNotFoundError:
                continue
            except OSError as e:
                logger.warning("audit open %s failed: %s", path, e)
                continue
            with f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        yield AuditEntry(**raw)
                    except Exception:
                        yield None

    def query_from_file(
        self,
        user: str = "",
        action: str = "",
        module: str = "",
        status: str = "",
        start_time: float = 0.0,
        end_time: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        paths = self._rotated_paths(reverse=False)
        results: list[AuditEntry] = []
        corrupted = 0
        buffer: list[AuditEntry] = []
        for entry in self._iter_file_entries(paths):
            if entry is None:
                corrupted += 1
                continue
            if not self._matches(entry, user, action, module, status, start_time, end_time):
                continue
            buffer.append(entry)
        for entry in reversed(buffer):
            results.append(entry)
            if len(results) >= offset + limit:
                break
        if corrupted:
            logger.warning("audit query skipped %d corrupted entries", corrupted)
        return results[offset : offset + limit]

    def _rotated_paths(self, reverse: bool = False) -> list[str]:
        base = self.log_path
        rotated = [f"{base}.{i}" for i in range(1, _MAX_ROTATED_FILES + 1)]
        rev = list(reversed(rotated))
        return rev + [base] if reverse else [base] + rev

    def get_stats(self) -> dict[str, Any]:
        stats = self._compute_stats(self._entries)
        stats["source"] = "in_memory"
        stats["warning"] = "in-memory stats only reflect the most recent 5000 entries; use /file-stats for full stats"
        return stats

    def get_stats_from_file(self) -> dict[str, Any]:
        entries: list[AuditEntry] = []
        corrupted = 0
        processed = 0
        paths = self._rotated_paths(reverse=False)
        for path in paths:
            try:
                f = open(path)
            except FileNotFoundError:
                continue
            except OSError as e:
                logger.warning("audit stats open %s failed: %s", path, e)
                continue
            with f:
                for line in f:
                    if processed >= _MAX_FILE_STATS_LINES:
                        logger.warning("audit stats capped at %d lines", _MAX_FILE_STATS_LINES)
                        break
                    processed += 1
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        entries.append(AuditEntry(**raw))
                    except Exception:
                        corrupted += 1
                        continue
        stats = self._compute_stats(entries)
        stats["corrupted_skipped"] = corrupted
        stats["source"] = "file"
        return stats

    def verify_chain(self) -> dict[str, Any]:
        paths = self._rotated_paths(reverse=False)
        prev_hash = _GENESIS_HASH
        index = 0
        broken: list[dict[str, Any]] = []
        checked = 0
        for entry in self._iter_file_entries(paths):
            if entry is None:
                continue
            index += 1
            checked += 1
            if entry.prev_hash != prev_hash:
                broken.append(
                    {"index": index, "reason": "prev_hash mismatch", "expected": prev_hash, "actual": entry.prev_hash}
                )
                prev_hash = entry.cur_hash or _GENESIS_HASH
                continue
            payload = _entry_payload(entry)
            expected_cur = _compute_cur_hash(prev_hash, payload)
            if entry.cur_hash != expected_cur:
                broken.append(
                    {"index": index, "reason": "cur_hash mismatch", "expected": expected_cur, "actual": entry.cur_hash}
                )
            prev_hash = entry.cur_hash or _GENESIS_HASH
        result = {"verified": not broken, "checked": checked, "broken_count": len(broken), "broken": broken[:20]}
        logger.info("audit chain verify: checked=%d broken=%d", checked, len(broken))
        return result

    def _compute_stats(self, entries: list[AuditEntry]) -> dict[str, Any]:
        if not entries:
            return {
                "total_entries": 0,
                "unique_users": 0,
                "unique_actions": 0,
                "unique_modules": 0,
                "success_rate": 0.0,
                "last_hour": 0,
                "action_counts": {},
                "module_counts": {},
                "hourly_distribution": {},
            }
        now = time.time()
        action_counts = Counter(e.action for e in entries)
        module_counts = Counter(e.module for e in entries)
        user_counts = Counter(e.user for e in entries)
        success_count = sum(1 for e in entries if e.status == "success")
        hourly = Counter()
        for e in entries:
            dt = datetime.fromtimestamp(e.timestamp)
            hourly[f"{dt.hour:02d}:00"] += 1
        avg_duration = 0.0
        durations = [e.duration_ms for e in entries if e.duration_ms > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
        return {
            "total_entries": len(entries),
            "unique_users": len(user_counts),
            "unique_actions": len(action_counts),
            "unique_modules": len(module_counts),
            "success_rate": round(success_count / len(entries), 4) if entries else 0.0,
            "last_hour": sum(1 for e in entries if now - e.timestamp < 3600),
            "avg_duration_ms": round(avg_duration, 2),
            "action_counts": dict(action_counts.most_common(20)),
            "module_counts": dict(module_counts.most_common(20)),
            "top_users": dict(user_counts.most_common(10)),
            "hourly_distribution": dict(sorted(hourly.items())),
        }
