from __future__ import annotations

import math
from typing import Any

from ..schema import Finding, MetricResult
from .common import empty_check_result, extract_numbers, input_value


def evidence_consistency(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    if not case.get("require_evidence_consistency"):
        return MetricResult("evidence_consistency", 100.0, True, [])

    tolerance = float(case.get("evidence_numeric_tolerance", 0.05))
    evidence_numbers = _numbers_by_entity(run.get("evidence", []))
    findings: list[Finding] = []
    checked = 0
    passed = 0

    for metric in run.get("metrics", []):
        entity = str(metric.get("entity", ""))
        numbers = evidence_numbers.get(entity, [])
        for input_name, raw_value in (metric.get("inputs") or {}).items():
            value = _to_float(input_value(raw_value))
            if value is None:
                continue
            checked += 1
            if _has_close_number(value, numbers, tolerance):
                passed += 1
                continue
            findings.append(
                Finding(
                    metric="evidence_consistency",
                    severity="high",
                    message=(
                        f"{entity} {metric.get('name')} input {input_name}={value} "
                        "is not supported by numeric evidence."
                    ),
                    recommendation="Check that cited evidence text contains the same financial input values used by the calculation.",
                )
            )

    if checked == 0:
        empty = empty_check_result(
            "evidence_consistency",
            case,
            detail="no metric inputs were available to compare against evidence text",
        )
        if empty is not None:
            return empty
        return MetricResult("evidence_consistency", 100.0, True, [])
    score = round(passed / checked * 100, 2)
    return MetricResult("evidence_consistency", score, not findings, findings)


def _numbers_by_entity(evidence: list[dict[str, Any]]) -> dict[str, list[float]]:
    by_entity: dict[str, list[float]] = {}
    for item in evidence:
        entity = str(item.get("entity", ""))
        by_entity.setdefault(entity, []).extend(extract_numbers(str(item.get("text") or "")))
    return by_entity


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_close_number(value: float, candidates: list[float], tolerance: float) -> bool:
    for candidate in candidates:
        if math.isclose(value, candidate, rel_tol=tolerance, abs_tol=tolerance):
            return True
    return False
