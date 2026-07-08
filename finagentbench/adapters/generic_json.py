from __future__ import annotations

from typing import Any


class GenericJsonAdapter:
    name = "generic"

    def can_parse(self, payload: dict[str, Any]) -> bool:
        return "run_id" in payload and "final_output" in payload

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)
