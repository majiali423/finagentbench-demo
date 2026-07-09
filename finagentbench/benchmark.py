from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import load_run_file
from .runner import evaluate_run


def run_benchmark_suite(suite_path: str | Path) -> dict[str, Any]:
    path = Path(suite_path)
    suite = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    case = json.loads((root / suite["case"]).resolve().read_text(encoding="utf-8"))

    items = []
    detected_failures = 0
    expected_failures = 0
    false_positives = 0
    covered_failure_types = set()

    for item in suite.get("items", []):
        run_path = (root / item["run"]).resolve()
        run = load_run_file(run_path, item.get("adapter", "auto"))
        report = evaluate_run(run, case)
        finding_metrics = {
            finding.metric
            for metric in report.metrics
            for finding in metric.findings
        }
        expected_findings = set(item.get("expected_findings", []))
        missing_findings = sorted(expected_findings - finding_metrics)
        expected_passed = bool(item.get("expected_passed", not expected_findings))
        failure_type = item.get("failure_type", "none")
        if failure_type != "none":
            covered_failure_types.add(failure_type)

        if expected_passed and not report.passed:
            false_positives += 1
        if not expected_passed:
            expected_failures += 1
            if not report.passed and not missing_findings:
                detected_failures += 1
        expectation_matched = report.passed == expected_passed

        items.append(
            {
                "id": item["id"],
                "run": str(run_path),
                "failure_type": failure_type,
                "expected_passed": expected_passed,
                "actual_passed": report.passed,
                "expectation_matched": expectation_matched,
                "score": report.score,
                "expected_findings": sorted(expected_findings),
                "actual_findings": sorted(finding_metrics),
                "missing_expected_findings": missing_findings,
            }
        )

    detection_rate = 1.0 if expected_failures == 0 else detected_failures / expected_failures
    passed = (
        false_positives == 0
        and all(item["expectation_matched"] for item in items)
        and all(not item["missing_expected_findings"] for item in items)
    )
    return {
        "suite_id": suite["id"],
        "case": suite["case"],
        "total_traces": len(items),
        "covered_failure_types": sorted(covered_failure_types),
        "covered_failure_type_count": len(covered_failure_types),
        "expected_failures": expected_failures,
        "detected_failures": detected_failures,
        "detection_rate": round(detection_rate, 4),
        "false_positives": false_positives,
        "passed": passed,
        "items": items,
    }


def run_semantic_benchmark_suite(suite_path: str | Path) -> dict[str, Any]:
    path = Path(suite_path)
    suite = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    task = suite.get("task", "evidence_support")
    metric_name = suite.get("metric", task)
    min_score = float(suite.get("min_score", 80.0))

    items = []
    false_positives = 0
    false_negatives = 0
    matched = 0
    by_failure_type: dict[str, dict[str, Any]] = {}

    for item in suite.get("items", []):
        run = _load_semantic_run(root, item)
        human_label = item["human_label"]
        expected_passed = bool(human_label["passed"])
        failure_type = str(human_label.get("failure_type", "supported"))
        case = _semantic_case(item, metric_name, min_score)
        report = evaluate_run(run, case)
        metric = next(result for result in report.metrics if result.name == metric_name)
        actual_passed = metric.passed
        expectation_matched = actual_passed == expected_passed
        if expectation_matched:
            matched += 1
        if expected_passed and not actual_passed:
            false_positives += 1
        if not expected_passed and actual_passed:
            false_negatives += 1

        bucket = by_failure_type.setdefault(
            failure_type,
            {"total": 0, "matched": 0, "detected": 0},
        )
        bucket["total"] += 1
        if expectation_matched:
            bucket["matched"] += 1
        if not expected_passed and not actual_passed:
            bucket["detected"] += 1

        items.append(
            {
                "id": item["id"],
                "task": task,
                "failure_type": failure_type,
                "human_passed": expected_passed,
                "actual_passed": actual_passed,
                "expectation_matched": expectation_matched,
                "score": metric.score,
                "human_severity": human_label.get("severity", ""),
                "actual_findings": [finding.message for finding in metric.findings],
            }
        )

    total = len(items)
    match_rate = 1.0 if total == 0 else matched / total
    return {
        "suite_id": suite["id"],
        "task": task,
        "metric": metric_name,
        "benchmark_mode": suite.get("benchmark_mode", "static_judge_replay"),
        "measures": "pipeline_replay_consistency_not_live_llm_accuracy",
        "total": total,
        "matched": matched,
        "replay_match_rate": round(match_rate, 4),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "by_failure_type": by_failure_type,
        "passed": false_positives == 0 and false_negatives == 0,
        "items": items,
    }


def _load_semantic_run(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    run = item.get("run")
    if isinstance(run, dict):
        return run
    if isinstance(run, str):
        return load_run_file((root / run).resolve(), item.get("adapter", "auto"))
    raise ValueError(f"Semantic benchmark item {item.get('id')} must provide a run object or run path")


def _semantic_case(item: dict[str, Any], metric_name: str, min_score: float) -> dict[str, Any]:
    return {
        "expected_entities": item.get("expected_entities", []),
        "required_steps": [],
        "enabled_metrics": [metric_name],
        "semantic_audit": {
            "judge": {
                "provider": "static",
                "results": {metric_name: item["judge_result"]},
            },
            f"min_{metric_name}_score": min_score,
        },
        "min_score": min_score,
    }
