from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)

# NOTE: compute_cache is process-local (in-memory OrderedDict). In a multi-node
# deployment each node maintains its own cache with no shared invalidation — a
# data update on node A leaves node B serving stale results until its local TTL
# expires. For multi-node consistency either keep TTLs short or front this with
# a shared cache (e.g. Redis) in a future iteration.


class DataCache:
    MAX_SIZE = 256
    DEFAULT_TTL = 3600

    def __init__(self, max_size: int = 0, default_ttl: int = 0):
        self._max_size = max_size or self.MAX_SIZE
        self._default_ttl = default_ttl or self.DEFAULT_TTL
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._inflight: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
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
        try:
            raw = json.dumps(parts, sort_keys=True, default=str)
        except (TypeError, ValueError) as e:
            logger.warning("make_key unhashable parts (%s); falling back to repr", e)
            raw = repr(type(p).__name__ for p in parts) + repr(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


_compute_cache = DataCache(max_size=128, default_ttl=1800)


def compute_cache(ttl: int = 0, namespace: str = ""):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            ns = namespace or fn.__module__ or ""
            try:
                key_payload = [ns, fn.__qualname__, args, sorted(kwargs.items())]
                cache_key = DataCache.make_key(*key_payload)
            except (TypeError, ValueError) as e:
                logger.warning(
                    "compute_cache: unhashable args for %s.%s (%s); skipping cache",
                    fn.__module__,
                    fn.__qualname__,
                    e,
                )
                return fn(*args, **kwargs)
            cached = _compute_cache.get(cache_key)
            if cached is not None:
                logger.debug("compute_cache hit: %s.%s", fn.__module__, fn.__qualname__)
                return cached
            with _compute_cache._lock:
                event = _compute_cache._inflight.get(cache_key)
                if event is None:
                    event = threading.Event()
                    _compute_cache._inflight[cache_key] = event
                    is_leader = True
                else:
                    is_leader = False
            if is_leader:
                try:
                    result = fn(*args, **kwargs)
                    _compute_cache.set(cache_key, result, ttl or _compute_cache._default_ttl)
                    logger.debug("compute_cache set: %s.%s", fn.__module__, fn.__qualname__)
                finally:
                    event.set()
                    with _compute_cache._lock:
                        _compute_cache._inflight.pop(cache_key, None)
                return result
            event.wait(timeout=30.0)
            cached = _compute_cache.get(cache_key)
            if cached is not None:
                logger.debug("compute_cache single-flight hit: %s.%s", fn.__module__, fn.__qualname__)
                return cached
            result = fn(*args, **kwargs)
            return result

        wrapper.__name__ = fn.__name__
        wrapper.__wrapped__ = fn
        return wrapper

    return decorator
