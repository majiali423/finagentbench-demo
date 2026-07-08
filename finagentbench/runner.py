from __future__ import annotations

from typing import Any

from .metrics.registry import resolve_metrics
from .schema import EvalReport, validate_case, validate_finrun


def evaluate_run(run: dict[str, Any], case: dict[str, Any]) -> EvalReport:
    validate_finrun(run)
    validate_case(case)
    results = [metric(run, case) for metric in resolve_metrics(case)]
    score = round(sum(result.score for result in results) / len(results), 2)
    passed = score >= float(case.get("min_score", 85)) and all(
        finding.severity != "critical"
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
