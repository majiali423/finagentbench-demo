from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def step_presence(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    expected = set(case.get("required_steps", []))
    actual = {step.get("name") for step in run.get("steps", [])}
    missing = sorted(expected - actual)
    findings = [
        Finding(
            metric="step_presence",
            severity="medium",
            message=f"Required step did not appear in trace: {step}",
            recommendation="Ensure the agent exports key workflow steps or maps them through an adapter.",
        )
        for step in missing
    ]
    score = 100.0 if not expected else round((len(expected) - len(missing)) / len(expected) * 100, 2)
    return MetricResult("step_presence", score, not findings, findings)
