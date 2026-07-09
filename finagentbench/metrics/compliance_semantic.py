from __future__ import annotations

from typing import Any

from ..schema import MetricResult
from .semantic_common import semantic_metric


def compliance_semantic(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    return semantic_metric(
        "compliance_semantic",
        run,
        case,
        85.0,
        "Semantic compliance risk detected",
        "Rewrite the answer to avoid personalized advice, guaranteed outcomes, and overconfident claims.",
    )
