from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def runtime_compliance(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    expected = case.get("expected_violation_codes")
    if expected is None:
        return MetricResult("runtime_compliance", 100.0, True, [])

    expected_codes = {str(code) for code in expected}
    metadata = run.get("metadata") or {}
    raw_violations = metadata.get("compliance_violations") or []
    actual_codes = {
        str(item.get("code"))
        for item in raw_violations
        if isinstance(item, dict) and item.get("code")
    }

    findings: list[Finding] = []
    unexpected = sorted(actual_codes - expected_codes)
    missing = sorted(expected_codes - actual_codes)

    for code in unexpected:
        findings.append(
            Finding(
                metric="runtime_compliance",
                severity="high",
                message=f"Unexpected runtime violation code exported: {code}",
                recommendation="Fix upstream critic checks or update case expected_violation_codes if intentional.",
                action="review",
                target={"code": code},
            )
        )
    for code in missing:
        findings.append(
            Finding(
                metric="runtime_compliance",
                severity="high",
                message=f"Expected runtime violation code missing from export: {code}",
                recommendation="Ensure LumenFin exports compliance_violations from critic node into FinRun metadata.",
                action="review",
                target={"code": code},
            )
        )

    passed = not findings
    score = 100.0 if passed else 0.0
    return MetricResult("runtime_compliance", score, passed, findings)
