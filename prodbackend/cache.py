# cache.py
"""
Lyra Engine Cache — simple, intern-friendly caching utilities.
"""
from __future__ import annotations

import time
import threading
from dataclasses import is_dataclass
from typing import Any, Dict, Optional, Tuple


def _as_primitive(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "value"):
        try:
            return obj.value
        except Exception:
            pass
    if is_dataclass(obj):
        return {k: _as_primitive(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {str(k): _as_primitive(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_as_primitive(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def build_cache_key(namespace: str, **kwargs: Any) -> str:
    prim = _as_primitive(kwargs)
    parts = [namespace]
    for k in sorted(prim.keys()):
        parts.append(f"{k}={prim[k]}")
    return "|".join(parts)


class TTLCache:
    def __init__(self, max_items: int = 5000, ttl_seconds: int = 3600) -> None:
        if max_items <= 0 or ttl_seconds <= 0:
            raise ValueError("max_items and ttl_seconds must be > 0")
        self.max_items = int(max_items)
        self.ttl_seconds = int(ttl_seconds)
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            inserted_at, value = item
            if now - inserted_at > self.ttl_seconds:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        with self._lock:
            self._data[key] = (now, value)
            self._evict_if_needed_locked()

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def purge(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            keys = list(self._data.keys())
            for k in keys:
                if now - self._data[k][0] > self.ttl_seconds:
                    self._data.pop(k, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def _evict_if_needed_locked(self) -> None:
        if len(self._data) <= self.max_items:
            return
        items = sorted(self._data.items(), key=lambda kv: kv[1][0])
        for i in range(len(items) - self.max_items):
            self._data.pop(items[i][0], None)


def cached_call(cache: TTLCache, key: str, fn, *args, **kwargs):
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = fn(*args, **kwargs)
    cache.set(key, value)
    return value
