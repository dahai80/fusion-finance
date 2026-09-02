from __future__ import annotations

import logging
import time
import uuid
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
MAX_SESSIONS = 100
MAX_MESSAGE_CHARS = 8000
MAX_SESSION_BYTES = 200_000
_TRUNCATED_SUFFIX = "...[truncated]"


def _cap_content(content: str) -> str:
    if not isinstance(content, str):
        content = str(content)
    if len(content) > MAX_MESSAGE_CHARS:
        keep = MAX_MESSAGE_CHARS - len(_TRUNCATED_SUFFIX)
        if keep < 0:
            return _TRUNCATED_SUFFIX[:MAX_MESSAGE_CHARS]
        return content[:keep] + _TRUNCATED_SUFFIX
    return content


class ConversationMemory:
    def __init__(self, max_history: int = 0, max_sessions: int = 0):
        self._max_history = max_history or MAX_HISTORY
        self._max_sessions = max_sessions or MAX_SESSIONS
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            self._ensure_capacity()
            self._sessions[session_id] = {
                "messages": [],
                "context": {},
                "created_at": time.time(),
                "byte_size": 0,
            }
        session = self._sessions[session_id]
        capped = _cap_content(content)
        msg = {
            "role": role,
            "content": capped,
            "timestamp": time.time(),
        }
        session["messages"].append(msg)
        session["byte_size"] += len(capped.encode("utf-8", errors="replace"))
        if len(session["messages"]) > self._max_history:
            dropped = session["messages"].pop(0)
            session["byte_size"] -= len(dropped["content"].encode("utf-8", errors="replace"))
            if session["byte_size"] < 0:
                session["byte_size"] = 0
        self._enforce_session_byte_cap(session_id)
        self._sessions.move_to_end(session_id)

    def get_messages(self, session_id: str, limit: int = 0) -> list[dict[str, str]]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        msgs = session["messages"]
        if limit:
            msgs = msgs[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in msgs]

    def set_context(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._sessions:
            self.add_message(session_id, "system", "session created")
        self._sessions[session_id]["context"][key] = value

    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        session = self._sessions.get(session_id)
        if not session:
            return default
        return session["context"].get(key, default)

    def get_full_context(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return {
            "messages": list(session["messages"]),
            "context": dict(session["context"]),
        }

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        result = []
        for sid, session in self._sessions.items():
            result.append(
                {
                    "session_id": sid,
                    "message_count": len(session["messages"]),
                    "created_at": session.get("created_at", 0),
                    "byte_size": session.get("byte_size", 0),
                }
            )
        return result

    def _ensure_capacity(self) -> None:
        while len(self._sessions) >= self._max_sessions:
            sid, _ = self._sessions.popitem(last=False)
            logger.debug("Evicted oldest session %s", sid)

    def _enforce_session_byte_cap(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        while session["byte_size"] > MAX_SESSION_BYTES and session["messages"]:
            dropped = session["messages"].pop(0)
            session["byte_size"] -= len(dropped["content"].encode("utf-8", errors="replace"))
            if session["byte_size"] < 0:
                session["byte_size"] = 0
            logger.warning(
                "session %s exceeded byte cap %d, evicted oldest message",
                session_id,
                MAX_SESSION_BYTES,
            )

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex[:12]
