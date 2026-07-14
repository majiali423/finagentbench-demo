from __future__ import annotations

from typing import Any

from .case_binding import resolve_case_for_run
from .metrics.registry import resolve_metrics
from .schema import EvalReport, validate_case, validate_finrun


def evaluate_run(run: dict[str, Any], case: dict[str, Any]) -> EvalReport:
    validate_finrun(run)
    validate_case(case)
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
    )


def compare_runs(baseline: dict[str, Any], current: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    base_report = evaluate_run(baseline, case)
    current_report = evaluate_run(current, case)
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
    }


def _score_results(results: list, case: dict[str, Any]) -> float:
    weights = case.get("metric_weights", {})
    weighted_total = 0.0
    weight_total = 0.0
    for result in results:
        weight = float(weights.get(result.name, 1.0))
        weighted_total += result.score * weight
        weight_total += weight
    score = 100.0 if weight_total == 0 else weighted_total / weight_total

    penalties = case.get("severity_penalties", {})
    for result in results:
        for finding in result.findings:
            score -= float(penalties.get(finding.severity, 0))
    return round(max(0.0, score), 2)
