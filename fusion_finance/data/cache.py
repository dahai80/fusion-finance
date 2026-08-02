from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class DataCache:
    MAX_SIZE = 256
    DEFAULT_TTL = 3600

    def __init__(self, max_size: int = 0, default_ttl: int = 0):
        self._max_size = max_size or self.MAX_SIZE
        self._default_ttl = default_ttl or self.DEFAULT_TTL
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()
        logger.info("DataCache initialized (max_size=%d, ttl=%ds)", self._max_size, self._default_ttl)

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires"]:
            del self._store[key]
            logger.debug("Cache expired: %s", key)
            return None
        self._store.move_to_end(key)
        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        expires = time.time() + (ttl or self._default_ttl)
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = {"value": value, "expires": expires}
        while len(self._store) > self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug("Cache evicted: %s", evicted_key)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def invalidate(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            logger.debug("Cache invalidated: %s", key)
            return True
        return False

    def clear(self) -> None:
        self._store.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        return len(self._store)

    @staticmethod
    def make_key(*parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
