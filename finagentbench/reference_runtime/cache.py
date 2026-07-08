from __future__ import annotations

from typing import Any


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    def get_or_set(self, key: str, factory) -> Any:
        if key in self._items:
            self.hits += 1
            return self._items[key]
        self.misses += 1
        value = factory()
        self._items[key] = value
        return value

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self._items)}
