from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..schema import MetricResult
from . import BUILTIN_METRICS


MetricFn = Callable[[dict[str, Any], dict[str, Any]], MetricResult]


def available_metrics() -> dict[str, MetricFn]:
    return {metric.__name__: metric for metric in BUILTIN_METRICS}


def resolve_metrics(case: dict[str, Any]) -> tuple[MetricFn, ...]:
    registry = available_metrics()
    enabled = case.get("enabled_metrics")
    if not enabled:
        return tuple(registry.values())

    missing = [name for name in enabled if name not in registry]
    if missing:
        names = ", ".join(sorted(registry))
        raise ValueError(f"Unknown metrics: {missing}. Available metrics: {names}")
    return tuple(registry[name] for name in enabled)
