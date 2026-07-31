from __future__ import annotations

import math
from typing import Any

from ..schema import Finding, MetricResult
from .common import input_unit, input_value


def input_value_plausibility(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    """Check metric input magnitudes against Case-configured bounds only."""
    bounds = case.get("input_value_bounds") or {}
    explicitly_enabled = "input_value_plausibility" in case.get("enabled_metrics", [])
    if not bounds and not explicitly_enabled:
        return MetricResult("input_value_plausibility", 100.0, True, [])
    if not isinstance(bounds, dict) or not bounds:
        return MetricResult("input_value_plausibility", 100.0, True, [])

    findings: list[Finding] = []
    checked = 0
    passed = 0

    for metric in run.get("metrics", []):
        inputs = metric.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        for name, payload in inputs.items():
            key = str(name or "").strip()
            rule = bounds.get(key)
            if not isinstance(rule, dict):
                continue
            unit = str(rule.get("unit") or "").strip()
            if not unit:
                continue
            actual_unit = input_unit(payload)
            if actual_unit != unit:
                # Unit mismatches belong to unit_currency_consistency; skip bound.
                continue
            checked += 1
            raw = input_value(payload)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                findings.append(
                    Finding(
                        metric="input_value_plausibility",
                        severity="critical",
                        message=(
                            f"{metric.get('entity')} {metric.get('name')} input {key} "
                            "is not a finite number (value outside case-configured bounds)."
                        ),
                        recommendation="Provide finite numeric inputs that satisfy the case bounds contract.",
                        target={"input": key, "code": "non_numeric"},
                    )
                )
                continue
            if not math.isfinite(value):
                findings.append(
                    Finding(
                        metric="input_value_plausibility",
                        severity="critical",
                        message=(
                            f"{metric.get('entity')} {metric.get('name')} input {key}={value} "
                            "is outside case-configured bounds."
                        ),
                        recommendation="Replace NaN/Infinity with finite values that satisfy the case bounds.",
                        target={"input": key, "code": "non_finite"},
                    )
                )
                continue
            try:
                minimum = float(rule["min"]) if "min" in rule else None
                maximum = float(rule["max"]) if "max" in rule else None
            except (TypeError, ValueError, KeyError):
                continue
            if minimum is not None and value < minimum:
                findings.append(_bound_finding(metric, key, value, unit))
                continue
            if maximum is not None and value > maximum:
                findings.append(_bound_finding(metric, key, value, unit))
                continue
            passed += 1

    if checked == 0:
        return MetricResult("input_value_plausibility", 100.0, True, [])
    score = round(passed / checked * 100, 2)
    return MetricResult("input_value_plausibility", score, not findings, findings)


def _bound_finding(metric: dict[str, Any], key: str, value: float, unit: str) -> Finding:
    return Finding(
        metric="input_value_plausibility",
        severity="critical",
        message=(
            f"{metric.get('entity')} {metric.get('name')} input {key}={value} {unit} "
            "is outside case-configured bounds."
        ),
        recommendation=(
            "Check unit normalization and source extraction; the value may be mis-scaled, "
            "but this finding only asserts a case-bounds violation."
        ),
        target={"input": key, "code": "outside_bounds"},
    )
