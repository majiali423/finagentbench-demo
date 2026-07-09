from __future__ import annotations

from typing import Any

from ..schema import MetricResult
from .semantic_common import semantic_metric


def risk_quality(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    return semantic_metric(
        "risk_quality",
        run,
        case,
        80.0,
        "Semantic risk disclosure quality is weak",
        "Rewrite risk disclosure so it is concrete, source-aware, and tied to the financial analysis.",
    )
