import time
from typing import Any, Optional


class TTLCache:
    """Simple in-process TTL cache keyed on arbitrary strings."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


lookup_cache = TTLCache()
