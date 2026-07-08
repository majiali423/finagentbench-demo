from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


RISK_TERMS = (
    "risk",
    "limitation",
    "uncertain",
    "volatility",
    "valuation",
    "drawdown",
    "incomplete",
    "not investment advice",
)


def risk_disclosure(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    if not case.get("require_risk_disclosure"):
        return MetricResult("risk_disclosure", 100.0, True, [])

    output = (run.get("final_output") or "").lower()
    has_risk_language = any(term in output for term in RISK_TERMS)
    has_research_boundary = "not investment advice" in output or "research output" in output
    findings = []
    if not has_risk_language:
        findings.append(
            Finding(
                metric="risk_disclosure",
                severity="high",
                message="Final output does not disclose material risks or limitations.",
                recommendation="Add risk, uncertainty, and limitation language for financial analysis outputs.",
            )
        )
    if not has_research_boundary:
        findings.append(
            Finding(
                metric="risk_disclosure",
                severity="medium",
                message="Final output does not clearly separate research from personalized investment advice.",
                recommendation="State that the output is research only and not investment advice.",
            )
        )
    score = 100.0 if not findings else max(0.0, 100.0 - 40.0 * len(findings))
    return MetricResult("risk_disclosure", score, not findings, findings)
