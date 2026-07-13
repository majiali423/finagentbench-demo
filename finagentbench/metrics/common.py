from __future__ import annotations

import re
from typing import Any

from ..schema import Finding, MetricResult


def empty_check_result(metric_name: str, case: dict[str, Any], *, detail: str) -> MetricResult | None:
    """Return a fail-closed result when a case requires checkable work but none was found."""
    if not case.get("require_checkable_metrics"):
        return None
    return MetricResult(
        metric_name,
        0.0,
        False,
        [
            Finding(
                metric=metric_name,
                severity="high",
                message=f"No checkable items for {metric_name}: {detail}",
                recommendation=(
                    "Export formula/inputs (or evidence numbers) so the metric can verify the run, "
                    "or disable require_checkable_metrics for intentionally non-quantitative cases."
                ),
                action="recompute" if metric_name == "numeric_correctness" else "retrieve",
            )
        ],
    )


def input_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def input_period(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("period") or "")
    return ""


def input_unit(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("unit") or "")
    return ""


def input_currency(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("currency") or "")
    return ""


def extract_numbers(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", text):
        raw = match.group(0).replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values
