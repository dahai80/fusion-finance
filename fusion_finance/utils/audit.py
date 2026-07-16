"""审计日志与合规追踪。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    """审计日志条目。"""
    timestamp: float = 0.0
    user: str = ""
    action: str = ""
    module: str = ""
    details: str = ""
    status: str = "success"
    duration_ms: float = 0.0


class AuditTrail:
    """审计日志 — 对标 Claude Financial 的可审计溯源要求。"""

    def __init__(self, log_path: str = ""):
        self.log_path = log_path or str(Path.home() / ".fusion" / "finance" / "audit.jsonl")
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []

    def record(self, user: str, action: str, module: str, details: str = "", status: str = "success"):
        entry = AuditEntry(timestamp=time.time(), user=user, action=action,
                          module=module, details=details, status=status)
        self._entries.append(entry)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry.__dict__) + "\n")
        return entry

    def query(self, user: str = "", action: str = "", module: str = "", limit: int = 100) -> List[AuditEntry]:
        results = []
        for e in reversed(self._entries):
            if user and e.user != user: continue
            if action and e.action != action: continue
            if module and e.module != module: continue
            results.append(e)
            if len(results) >= limit: break
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "unique_users": len(set(e.user for e in self._entries)),
            "unique_actions": len(set(e.action for e in self._entries)),
            "last_hour": sum(1 for e in self._entries if time.time() - e.timestamp < 3600),
        }