from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

FINRUN_SCHEMA_VERSION = "1.0"
SUPPORTED_FINRUN_SCHEMA_VERSIONS = frozenset({"0", FINRUN_SCHEMA_VERSION})
DEFAULT_SCORING_VERSION = "1"
SUPPORTED_SCORING_VERSIONS = frozenset({DEFAULT_SCORING_VERSION, "2"})


@dataclass(frozen=True)
class Finding:
    metric: str
    severity: str
    message: str
    recommendation: str = ""
    action: str = ""
    target: dict[str, Any] = field(default_factory=dict)


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
    tool_version: str = ""
    case_id: str = ""
    case_hash: str = ""
    profile: str = ""
    adapter: str = ""
    enabled_metrics: list[str] = field(default_factory=list)
    scoring_version: str = DEFAULT_SCORING_VERSION


class ValidationError(ValueError):
    pass


def validate_finrun(run: dict[str, Any]) -> None:
    schema_version = str(run.get("schema_version") or "0")
    if schema_version not in SUPPORTED_FINRUN_SCHEMA_VERSIONS:
        raise ValidationError(
            f"Unsupported FinRun schema_version={schema_version}; "
            f"supported={sorted(SUPPORTED_FINRUN_SCHEMA_VERSIONS)}"
        )
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
    scoring_version = str(case.get("scoring_version") or DEFAULT_SCORING_VERSION)
    if scoring_version not in SUPPORTED_SCORING_VERSIONS:
        raise ValidationError(
            f"Unsupported scoring_version={scoring_version}; "
            f"supported={sorted(SUPPORTED_SCORING_VERSIONS)}"
        )
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
    if "entity_aliases" in case:
        if not isinstance(case["entity_aliases"], dict):
            raise ValidationError("entity_aliases must be an object")
        for key, aliases in case["entity_aliases"].items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError("entity_aliases keys must be non-empty strings")
            if isinstance(aliases, str):
                continue
            if not isinstance(aliases, list) or not all(
                isinstance(item, str) for item in aliases
            ):
                raise ValidationError(
                    f"entity_aliases.{key} must be a string or list of strings"
                )
    if "peer_section_aliases" in case:
        _require_list(case, "peer_section_aliases")
        for item in case["peer_section_aliases"]:
            if not isinstance(item, str) or not item.strip():
                raise ValidationError("peer_section_aliases items must be non-empty strings")
    if "input_value_bounds" in case:
        _validate_input_value_bounds(case["input_value_bounds"])


def _validate_input_value_bounds(bounds: Any) -> None:
    if not isinstance(bounds, dict):
        raise ValidationError("input_value_bounds must be an object")
    for name, rule in bounds.items():
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("input_value_bounds metric keys must be non-empty strings")
        if not isinstance(rule, dict):
            raise ValidationError(f"input_value_bounds.{name} must be an object")
        unit = rule.get("unit")
        if not isinstance(unit, str) or not unit.strip():
            raise ValidationError(f"input_value_bounds.{name}.unit must be a non-empty string")
        if "min" not in rule and "max" not in rule:
            raise ValidationError(f"input_value_bounds.{name} requires min and/or max")
        minimum = maximum = None
        if "min" in rule:
            try:
                minimum = float(rule["min"])
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"input_value_bounds.{name}.min must be numeric") from exc
            if not math.isfinite(minimum):
                raise ValidationError(f"input_value_bounds.{name}.min must be finite")
        if "max" in rule:
            try:
                maximum = float(rule["max"])
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"input_value_bounds.{name}.max must be numeric") from exc
            if not math.isfinite(maximum):
                raise ValidationError(f"input_value_bounds.{name}.max must be finite")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValidationError(f"input_value_bounds.{name}.min must be <= max")


def _require_list(payload: dict[str, Any], field_name: str) -> None:
    if field_name not in payload:
        raise ValidationError(f"Missing required list field: {field_name}")
    if not isinstance(payload[field_name], list):
        raise ValidationError(f"{field_name} must be a list")
