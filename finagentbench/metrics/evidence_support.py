from __future__ import annotations

from typing import Any

from ..llm import build_judge
from ..schema import Finding, MetricResult


def evidence_support(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    config = case.get("semantic_audit", {})
    min_score = float(config.get("min_evidence_support_score", 80.0))
    judge = build_judge(config.get("judge", {}))
    result = judge.judge(
        "evidence_support",
        {
            "query": run.get("query", case.get("query", "")),
            "entities": run.get("entities", []),
            "final_output": run.get("final_output", ""),
            "evidence": run.get("evidence", []),
            "metrics": run.get("metrics", []),
        },
    )
    passed = result.passed and result.score >= min_score
    findings = []
    if not passed:
        findings.append(
            Finding(
                metric="evidence_support",
                severity=result.severity,
                message=f"Semantic evidence support is weak: {result.rationale}",
                recommendation="Review unsupported claims, retrieve stronger evidence, or rewrite the conclusion.",
                action="review",
                target={"section": "final_output", "labels": result.labels},
            )
        )
    return MetricResult("evidence_support", round(result.score, 2), passed, findings)
