from __future__ import annotations

from typing import Any

from ..schema import MetricResult
from .semantic_common import semantic_metric


def evidence_support(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    return semantic_metric(
        "evidence_support",
        run,
        case,
        80.0,
        "Semantic evidence support is weak",
        "Review unsupported claims, retrieve stronger evidence, or rewrite the conclusion.",
    )
