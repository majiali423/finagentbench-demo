from __future__ import annotations

from typing import Any, Protocol


class TraceAdapter(Protocol):
    name: str

    def can_parse(self, payload: dict[str, Any]) -> bool:
        ...

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...
