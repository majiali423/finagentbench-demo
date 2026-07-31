from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult
from .common import empty_check_result, input_currency, input_unit, input_value

# Annual revenue on a billion-USD scale above this is almost always a unit bug
# (e.g. SEC "(In millions)" values published as billion_usd without scaling).
_ABSURD_BILLION_USD_CEILING = 1000.0
_ABSURD_INPUT_NAMES = frozenset({"revenue", "ebitda", "operating_income", "r_and_d", "rd"})


def unit_currency_consistency(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    explicitly_enabled = "unit_currency_consistency" in case.get("enabled_metrics", [])
    if not case.get("require_unit_currency_consistency") and not explicitly_enabled:
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

        absurd = _absurd_billion_inputs(inputs)
        if absurd:
            findings.append(
                Finding(
                    metric="unit_currency_consistency",
                    severity="critical",
                    message=(
                        f"{metric.get('entity')} {metric.get('name')} has absurd billion-scale "
                        f"input(s): {absurd}. Likely millions labeled as billions."
                    ),
                    recommendation=(
                        "Normalize document-extracted absolutes to billion USD "
                        f"(reject magnitudes above {_ABSURD_BILLION_USD_CEILING})."
                    ),
                )
            )
            continue
        passed += 1

    if checked == 0:
        empty = empty_check_result(
            "unit_currency_consistency",
            case,
            detail="no metric inputs with unit/currency metadata were exported",
        )
        if empty is not None:
            return empty
        return MetricResult("unit_currency_consistency", 100.0, True, [])
    score = round(passed / checked * 100, 2)
    return MetricResult("unit_currency_consistency", score, not findings, findings)


def _absurd_billion_inputs(inputs: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for name, payload in inputs.items():
        key = str(name or "").strip().lower()
        if key not in _ABSURD_INPUT_NAMES:
            continue
        unit = input_unit(payload).lower()
        if unit not in {"billion", "billion_usd", "bn", "usd_billion"}:
            continue
        try:
            value = float(input_value(payload))
        except (TypeError, ValueError):
            continue
        if value > _ABSURD_BILLION_USD_CEILING:
            hits.append(f"{name}={value} {unit}")
    return hits


def _finding(metric: dict[str, Any], reason: str) -> Finding:
    return Finding(
        metric="unit_currency_consistency",
        severity="critical",
        message=f"{metric.get('entity')} {metric.get('name')} has {reason}.",
        recommendation="Normalize financial inputs to explicit units and currencies before computing ratios.",
    )
