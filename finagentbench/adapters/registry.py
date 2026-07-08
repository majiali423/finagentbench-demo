from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import TraceAdapter
from .agent_state import AgentStateAdapter
from .generic_json import GenericJsonAdapter


ADAPTERS: tuple[TraceAdapter, ...] = (GenericJsonAdapter(), AgentStateAdapter())


def load_run_file(path: str | Path, adapter_name: str = "auto") -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_run(payload, adapter_name)


def normalize_run(payload: dict[str, Any], adapter_name: str = "auto") -> dict[str, Any]:
    if adapter_name != "auto":
        for adapter in ADAPTERS:
            if adapter.name == adapter_name:
                return adapter.normalize(payload)
        names = ", ".join(adapter.name for adapter in ADAPTERS)
        raise ValueError(f"Unknown adapter '{adapter_name}'. Available adapters: {names}")

    for adapter in ADAPTERS:
        if adapter.can_parse(payload):
            return adapter.normalize(payload)
    raise ValueError("Could not infer run adapter. Pass --adapter explicitly.")
