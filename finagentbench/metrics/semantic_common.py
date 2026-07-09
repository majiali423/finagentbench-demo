from __future__ import annotations

from typing import Any

from ..llm import build_judge
from ..schema import Finding, MetricResult


def semantic_metric(
    name: str,
    run: dict[str, Any],
    case: dict[str, Any],
    default_min_score: float,
    failure_message: str,
    recommendation: str,
) -> MetricResult:
    config = case.get("semantic_audit", {})
    min_score = float(config.get(f"min_{name}_score", default_min_score))
    judge = build_judge(config.get("judge", {}))
    result = judge.judge(
        name,
        {
            "query": run.get("query", case.get("query", "")),
            "entities": run.get("entities", []),
            "steps": run.get("steps", []),
            "metrics": run.get("metrics", []),
            "evidence": run.get("evidence", []),
            "market_data": run.get("market_data", []),
            "final_output": run.get("final_output", ""),
        },
    )
    passed = result.passed and result.score >= min_score
    findings = []
    if not passed:
        findings.append(
            Finding(
                metric=name,
                severity=result.severity,
                message=f"{failure_message}: {result.rationale}",
                recommendation=recommendation,
                action="review",
                target={
                    "section": "final_output",
                    "labels": result.labels,
                    "judge": result.metadata,
                },
            )
        )
    return MetricResult(name, round(result.score, 2), passed, findings)
