from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult
from .common import input_period


def temporal_consistency(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    if not case.get("require_temporal_consistency"):
        return MetricResult("temporal_consistency", 100.0, True, [])

    findings: list[Finding] = []
    checked = 0
    passed = 0

    for metric in run.get("metrics", []):
        checked += 1
        metric_period = str(metric.get("period") or "")
        input_periods = {input_period(value) for value in (metric.get("inputs") or {}).values()}
        input_periods.discard("")
        if not metric_period:
            findings.append(_finding(f"{metric.get('entity')} {metric.get('name')} has no period."))
            continue
        if input_periods and input_periods != {metric_period}:
            findings.append(
                _finding(
                    f"{metric.get('entity')} {metric.get('name')} mixes metric period "
                    f"{metric_period} with input periods {sorted(input_periods)}."
                )
            )
            continue
        passed += 1

    for item in run.get("evidence", []):
        checked += 1
        if item.get("period"):
            passed += 1
        else:
            findings.append(_finding(f"Evidence for {item.get('entity', 'unknown')} has no period."))

    for item in run.get("market_data", []):
        checked += 1
        if item.get("as_of"):
            passed += 1
        else:
            findings.append(_finding(f"Market data for {item.get('entity', 'unknown')} has no as_of date."))

    score = 100.0 if checked == 0 else round(passed / checked * 100, 2)
    return MetricResult("temporal_consistency", score, not findings, findings)


def _finding(message: str) -> Finding:
    return Finding(
        metric="temporal_consistency",
        severity="critical",
        message=message,
        recommendation="Attach reporting periods to financial metrics/evidence and as_of dates to market data.",
    )
