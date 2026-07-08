from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    metric: str
    severity: str
    message: str
    recommendation: str = ""


@dataclass(frozen=True)
class MetricResult:
    name: str
    score: float
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True)
class EvalReport:
    run_id: str
    score: float
    passed: bool
    metrics: list[MetricResult]


class ValidationError(ValueError):
    pass


def validate_finrun(run: dict[str, Any]) -> None:
    required_fields = ("run_id", "final_output")
    for field_name in required_fields:
        if field_name not in run:
            raise ValidationError(f"FinRun missing required field: {field_name}")
    _require_list(run, "entities")
    _require_list(run, "steps")
    _require_list(run, "metrics")
    _require_list(run, "evidence")
    _require_list(run, "market_data")
    if not isinstance(run["final_output"], str):
        raise ValidationError("FinRun final_output must be a string")


def validate_case(case: dict[str, Any]) -> None:
    _require_list(case, "expected_entities")
    _require_list(case, "required_steps")
    if "min_score" in case:
        float(case["min_score"])
    if "numeric_tolerance" in case:
        float(case["numeric_tolerance"])
    if "enabled_metrics" in case:
        _require_list(case, "enabled_metrics")
    if "required_sections" in case:
        _require_list(case, "required_sections")
    if "metric_weights" in case and not isinstance(case["metric_weights"], dict):
        raise ValidationError("metric_weights must be an object")
    if "severity_penalties" in case and not isinstance(case["severity_penalties"], dict):
        raise ValidationError("severity_penalties must be an object")
    if "block_on_severity" in case:
        _require_list(case, "block_on_severity")


def _require_list(payload: dict[str, Any], field_name: str) -> None:
    if field_name not in payload:
        raise ValidationError(f"Missing required list field: {field_name}")
    if not isinstance(payload[field_name], list):
        raise ValidationError(f"{field_name} must be a list")
