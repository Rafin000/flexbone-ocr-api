"""A tiny thread-safe LRU cache for OCR results (bonus: caching identical
images). In-memory and per-instance — fine for this service; a shared store
like Redis would be the next step for multi-instance caching."""
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional


class LruCache:
    def __init__(self, max_entries: int = 128) -> None:
        self._store: "OrderedDict[str, Any]" = OrderedDict()
        self._max = max_entries
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)  # mark as recently used
            return self._store[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            if len(self._store) > self._max:
                self._store.popitem(last=False)  # evict least-recently used


# Shared instance, sized from config at app startup.
ocr_cache = LruCache()
