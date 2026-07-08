from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult
from .common import input_currency, input_unit


def unit_currency_consistency(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    if not case.get("require_unit_currency_consistency"):
        return MetricResult("unit_currency_consistency", 100.0, True, [])

    findings: list[Finding] = []
    checked = 0
    passed = 0

    for metric in run.get("metrics", []):
        inputs = metric.get("inputs") or {}
        if not inputs:
            continue
        checked += 1
        units = {input_unit(value) for value in inputs.values()}
        currencies = {input_currency(value) for value in inputs.values()}
        units.discard("")
        currencies.discard("")

        if len(units) != 1:
            findings.append(_finding(metric, f"mixed or missing units: {sorted(units)}"))
            continue
        if len(currencies) != 1:
            findings.append(_finding(metric, f"mixed or missing currencies: {sorted(currencies)}"))
            continue
        passed += 1

    score = 100.0 if checked == 0 else round(passed / checked * 100, 2)
    return MetricResult("unit_currency_consistency", score, not findings, findings)


def _finding(metric: dict[str, Any], reason: str) -> Finding:
    return Finding(
        metric="unit_currency_consistency",
        severity="critical",
        message=f"{metric.get('entity')} {metric.get('name')} has {reason}.",
        recommendation="Normalize financial inputs to explicit units and currencies before computing ratios.",
    )
