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
