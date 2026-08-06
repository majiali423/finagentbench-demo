from __future__ import annotations

import math
from typing import Any

from .case_binding import resolve_case_for_run
from .metrics.registry import resolve_metrics
from .schema import DEFAULT_SCORING_VERSION, EvalReport, ValidationError, validate_case, validate_finrun


def evaluate_run(run: dict[str, Any], case: dict[str, Any]) -> EvalReport:
    validate_finrun(run)
    validate_case(case)
    original_derive = bool(case.get("derive_entities_from_run"))
    case_mode = str(case.get("case_mode") or "quality")
    case = resolve_case_for_run(run, case)
    results = [metric(run, case) for metric in resolve_metrics(case)]
    score = _score_results(results, case)
    blocked = set(case.get("block_on_severity", ["critical"]))
    passed = score >= float(case.get("min_score", 85)) and all(
        finding.severity not in blocked
        for result in results
        for finding in result.findings
    )
    return EvalReport(
        run_id=str(run.get("run_id", "unknown")),
        score=score,
        passed=passed,
        metrics=results,
        scoring_version=str(case.get("scoring_version") or DEFAULT_SCORING_VERSION),
        case_mode=case_mode,
        derived_expectations=original_derive,
    )


def compare_runs(baseline: dict[str, Any], current: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    validate_finrun(baseline)
    validate_finrun(current)
    validate_case(case)
    # Freeze expectations once so derive_entities_from_run cannot invent two
    # different expected entity sets and hide entity regressions.
    frozen_case = dict(case)
    derived = bool(frozen_case.get("derive_entities_from_run"))
    if derived:
        frozen_case = resolve_case_for_run(baseline, frozen_case)
        frozen_case["derive_entities_from_run"] = False
    base_report = evaluate_run(baseline, frozen_case)
    current_report = evaluate_run(current, frozen_case)
    base_scores = {metric.name: metric.score for metric in base_report.metrics}
    current_scores = {metric.name: metric.score for metric in current_report.metrics}
    deltas = {
        name: round(current_scores[name] - base_scores.get(name, 0), 2)
        for name in current_scores
    }
    regressions = {
        name: delta
        for name, delta in deltas.items()
        if delta < -float(case.get("regression_tolerance", 5))
    }
    return {
        "baseline_run_id": base_report.run_id,
        "current_run_id": current_report.run_id,
        "baseline_score": base_report.score,
        "current_score": current_report.score,
        "score_delta": round(current_report.score - base_report.score, 2),
        "regressions": regressions,
        "passed": current_report.passed and not regressions,
        "case_mode": str(case.get("case_mode") or "quality"),
        "derived_expectations_frozen_from_baseline": derived,
    }


def _score_results(results: list, case: dict[str, Any]) -> float:
    weights = case.get("metric_weights", {})
    if weights is None:
        weights = {}
    if not isinstance(weights, dict):
        raise ValidationError("metric_weights must be an object")

    weighted_total = 0.0
    weight_total = 0.0
    for result in results:
        if not math.isfinite(float(result.score)):
            raise ValidationError(
                f"metric {result.name} returned a non-finite score: {result.score}"
            )
        score = float(result.score)
        if score < 0 or score > 100:
            raise ValidationError(
                f"metric {result.name} score must be between 0 and 100, got {score}"
            )
        raw_weight = weights.get(result.name, 1.0)
        if isinstance(raw_weight, bool):
            raise ValidationError(
                f"metric_weights.{result.name} must be a finite non-negative number"
            )
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0:
            raise ValidationError(
                f"metric_weights.{result.name} must be a finite non-negative number"
            )
        weighted_total += score * weight
        weight_total += weight

    if weight_total == 0:
        score = 100.0
    else:
        score = weighted_total / weight_total

    penalties = case.get("severity_penalties", {}) or {}
    if not isinstance(penalties, dict):
        raise ValidationError("severity_penalties must be an object")
    for result in results:
        for finding in result.findings:
            raw_penalty = penalties.get(finding.severity, 0)
            if isinstance(raw_penalty, bool):
                raise ValidationError(
                    f"severity_penalties.{finding.severity} must be a finite non-negative number"
                )
            penalty = float(raw_penalty)
            if not math.isfinite(penalty) or penalty < 0:
                raise ValidationError(
                    f"severity_penalties.{finding.severity} must be a finite non-negative number"
                )
            score -= penalty

    if not math.isfinite(score):
        raise ValidationError(f"aggregate score must be finite, got {score}")
    # Floor only; never invent an upper clamp that hides overshoot from bad metrics.
    score = max(0.0, score)
    if score > 100:
        raise ValidationError(f"aggregate score must be <= 100, got {score}")
    return round(score, 2)
