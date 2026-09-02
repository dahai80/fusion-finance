from __future__ import annotations

import json
import logging
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


@dataclass
class AuditEntry:
    timestamp: float = 0.0
    user: str = ""
    action: str = ""
    module: str = ""
    details: str = ""
    status: str = "success"
    duration_ms: float = 0.0


def get_audit_trail(log_path: str = "") -> AuditTrail:
    global _AUDIT_SINGLETON
    if _AUDIT_SINGLETON is None or log_path:
        _AUDIT_SINGLETON = AuditTrail(log_path)
    return _AUDIT_SINGLETON


class AuditTrail:
    def __init__(self, log_path: str = ""):
        self.log_path = log_path or str(Path.home() / ".fusion" / "finance" / "audit.jsonl")
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[AuditEntry] = []
        self._corrupted_count = 0

    def record(
        self, user: str, action: str, module: str, details: str = "", status: str = "success", duration_ms: float = 0.0
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            user=user,
            action=action,
            module=module,
            details=details,
            status=status,
            duration_ms=duration_ms,
        )
        self._entries.append(entry)
        if len(self._entries) > _MAX_INMEMORY_ENTRIES:
            self._entries = self._entries[-_MAX_INMEMORY_ENTRIES:]
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.__dict__) + "\n")
        except Exception as e:
            logger.error("Failed to write audit entry: %s", e)
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
        results = []
        corrupted = 0
        try:
            with open(self.log_path) as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                e = AuditEntry(**raw)
            except Exception:
                corrupted += 1
                continue
            if user and e.user != user:
                continue
            if action and e.action != action:
                continue
            if module and e.module != module:
                continue
            if status and e.status != status:
                continue
            if start_time and e.timestamp < start_time:
                continue
            if end_time and e.timestamp > end_time:
                continue
            results.append(e)
            if len(results) >= offset + limit:
                break
        if corrupted:
            logger.warning("audit query skipped %d corrupted entries", corrupted)
        return results[offset : offset + limit]

    def get_stats(self) -> dict[str, Any]:
        return self._compute_stats(self._entries)

    def get_stats_from_file(self) -> dict[str, Any]:
        entries = []
        corrupted = 0
        processed = 0
        try:
            with open(self.log_path) as f:
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
        except FileNotFoundError:
            pass
        stats = self._compute_stats(entries)
        stats["corrupted_skipped"] = corrupted
        return stats

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
