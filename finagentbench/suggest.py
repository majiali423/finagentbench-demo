from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .schema import EvalReport, Finding


ACTION_BY_METRIC = {
    "entity_coverage": "replan",
    "step_presence": "rerun",
    "section_presence": "rewrite",
    "numeric_correctness": "recompute",
    "temporal_consistency": "normalize",
    "unit_currency_consistency": "normalize",
    "evidence_coverage": "retrieve",
    "evidence_consistency": "retrieve",
    "market_data_disclosure": "disclose",
    "risk_disclosure": "rewrite",
    "compliance_language": "rewrite",
}


def build_suggestions(report: EvalReport) -> dict[str, Any]:
    actions = []
    for metric in report.metrics:
        for finding in metric.findings:
            actions.append(_finding_to_action(finding))
    return {
        "run_id": report.run_id,
        "score": report.score,
        "passed": report.passed,
        "actions": actions,
    }


def _finding_to_action(finding: Finding) -> dict[str, Any]:
    return {
        "action": ACTION_BY_METRIC.get(finding.metric, "review"),
        "target": _target_for(finding),
        "reason": finding.message,
        "metric": finding.metric,
        "severity": finding.severity,
        "recommendation": finding.recommendation,
    }


def _target_for(finding: Finding) -> dict[str, Any]:
    message = finding.message
    if finding.metric in {"entity_coverage", "evidence_coverage"}:
        return {"entity": _after_last_colon(message)}
    if finding.metric == "step_presence":
        return {"step": _after_last_colon(message)}
    if finding.metric in {"numeric_correctness", "evidence_consistency"}:
        return _calculation_target(message)
    if finding.metric == "section_presence":
        return {"section": _after_last_colon(message)}
    if finding.metric == "market_data_disclosure":
        return {"entity": _between(message, "for ", " but") or "unknown"}
    if finding.metric in {"risk_disclosure", "compliance_language"}:
        return {"section": "final_output"}
    return asdict(finding)


def _after_last_colon(value: str) -> str:
    return value.rsplit(":", 1)[-1].strip()


def _between(value: str, start: str, end: str) -> str:
    start_index = value.find(start)
    if start_index == -1:
        return ""
    start_index += len(start)
    end_index = value.find(end, start_index)
    if end_index == -1:
        return value[start_index:].strip()
    return value[start_index:end_index].strip()


def _calculation_target(message: str) -> dict[str, str]:
    if " input " in message:
        prefix, rest = message.split(" input ", 1)
        field = rest.split("=", 1)[0]
        return {"calculation": prefix.strip(), "field": field.strip()}
    return {"calculation": message.split(" mismatch:", 1)[0].strip()}
