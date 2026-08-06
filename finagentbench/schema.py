from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

FINRUN_SCHEMA_VERSION = "1.0"
SUPPORTED_FINRUN_SCHEMA_VERSIONS = frozenset({"0", FINRUN_SCHEMA_VERSION})
DEFAULT_SCORING_VERSION = "1"
SUPPORTED_SCORING_VERSIONS = frozenset({DEFAULT_SCORING_VERSION, "2"})
SUPPORTED_CASE_MODES = frozenset({"quality", "compatibility"})
SUPPORTED_SEVERITIES = frozenset({"critical", "high", "medium", "low"})


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
    case_mode: str = "quality"
    derived_expectations: bool = False


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

    for index, entity in enumerate(run["entities"]):
        _validate_entity(entity, f"entities[{index}]")
    for index, step in enumerate(run["steps"]):
        _validate_step(step, f"steps[{index}]")
    for index, metric in enumerate(run["metrics"]):
        _validate_metric(metric, f"metrics[{index}]")
    for index, item in enumerate(run["evidence"]):
        _validate_evidence(item, f"evidence[{index}]")
    for index, item in enumerate(run["market_data"]):
        _validate_market_data(item, f"market_data[{index}]")
    if "claims" in run:
        if not isinstance(run["claims"], list):
            raise ValidationError("claims must be a list")
        for index, claim in enumerate(run["claims"]):
            _validate_claim(claim, f"claims[{index}]")


def validate_case(case: dict[str, Any]) -> None:
    scoring_version = str(case.get("scoring_version") or DEFAULT_SCORING_VERSION)
    if scoring_version not in SUPPORTED_SCORING_VERSIONS:
        raise ValidationError(
            f"Unsupported scoring_version={scoring_version}; "
            f"supported={sorted(SUPPORTED_SCORING_VERSIONS)}"
        )

    case_mode = str(case.get("case_mode") or "quality")
    if case_mode not in SUPPORTED_CASE_MODES:
        raise ValidationError(
            f"case_mode must be one of {sorted(SUPPORTED_CASE_MODES)}"
        )
    derive = bool(case.get("derive_entities_from_run"))
    allow_derived = bool(case.get("allow_derived_expectations"))
    if derive and case_mode != "compatibility" and not allow_derived:
        raise ValidationError(
            "derive_entities_from_run requires case_mode=compatibility "
            "(or allow_derived_expectations=true); quality cases must fix expected_entities"
        )

    _require_list(case, "expected_entities")
    _require_list(case, "required_steps")
    _validate_non_empty_string_list(case["expected_entities"], "expected_entities", allow_empty_list=True)
    _validate_non_empty_string_list(case["required_steps"], "required_steps", allow_empty_list=True)

    _validate_finite_range(
        case,
        "min_score",
        minimum=0.0,
        maximum=100.0,
        required=False,
    )
    for field_name in (
        "numeric_tolerance",
        "evidence_numeric_tolerance",
        "regression_tolerance",
    ):
        _validate_finite_non_negative(case, field_name)

    registered = _registered_metric_names()
    if "enabled_metrics" in case:
        _require_list(case, "enabled_metrics")
        _validate_metric_name_list(case["enabled_metrics"], "enabled_metrics", registered)

    if "required_sections" in case:
        _require_list(case, "required_sections")
        _validate_non_empty_string_list(
            case["required_sections"],
            "required_sections",
            allow_empty_list=True,
        )

    if "metric_weights" in case:
        if not isinstance(case["metric_weights"], dict):
            raise ValidationError("metric_weights must be an object")
        weight_sum = 0.0
        for name, raw in case["metric_weights"].items():
            path = f"metric_weights.{name}"
            if not isinstance(name, str) or not name.strip():
                raise ValidationError("metric_weights keys must be non-empty strings")
            if name not in registered:
                raise ValidationError(f"metric_weights contains unknown metric: {name}")
            weight = _require_finite_number(raw, path, allow_negative=False)
            weight_sum += weight
        if case["metric_weights"] and not math.isfinite(weight_sum):
            raise ValidationError("metric_weights total must be a finite number")
        if case["metric_weights"] and weight_sum < 0:
            raise ValidationError("metric_weights total must be non-negative")

    if "severity_penalties" in case:
        if not isinstance(case["severity_penalties"], dict):
            raise ValidationError("severity_penalties must be an object")
        for name, raw in case["severity_penalties"].items():
            path = f"severity_penalties.{name}"
            if name not in SUPPORTED_SEVERITIES:
                raise ValidationError(f"severity_penalties contains unsupported severity: {name}")
            _require_finite_number(raw, path, allow_negative=False)

    if "block_on_severity" in case:
        _require_list(case, "block_on_severity")
        seen: set[str] = set()
        for index, item in enumerate(case["block_on_severity"]):
            path = f"block_on_severity[{index}]"
            if not isinstance(item, str) or not item.strip():
                raise ValidationError(f"{path} must be a non-empty string")
            if item not in SUPPORTED_SEVERITIES:
                raise ValidationError(f"block_on_severity contains unknown severity: {item}")
            if item in seen:
                raise ValidationError(f"block_on_severity contains duplicate severity: {item}")
            seen.add(item)

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


def _registered_metric_names() -> set[str]:
    # Local import avoids circular import at module load.
    from .metrics.registry import available_metrics

    return set(available_metrics())


def _validate_finite_range(
    payload: dict[str, Any],
    field_name: str,
    *,
    minimum: float,
    maximum: float,
    required: bool,
) -> None:
    if field_name not in payload:
        if required:
            raise ValidationError(f"{field_name} is required")
        return
    value = _require_finite_number(payload[field_name], field_name, allow_negative=True)
    if value < minimum or value > maximum:
        raise ValidationError(f"{field_name} must be between {minimum:g} and {maximum:g}")


def _validate_finite_non_negative(payload: dict[str, Any], field_name: str) -> None:
    if field_name not in payload:
        return
    _require_finite_number(payload[field_name], field_name, allow_negative=False)


def _require_finite_number(raw: Any, path: str, *, allow_negative: bool) -> float:
    # Reject bool explicitly: bool is a int subclass and float(True) == 1.0.
    if isinstance(raw, bool):
        raise ValidationError(
            f"{path} must be a finite non-negative number"
            if not allow_negative
            else f"{path} must be a finite number"
        )
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{path} must be a finite non-negative number"
            if not allow_negative
            else f"{path} must be a finite number"
        ) from exc
    if not math.isfinite(value):
        raise ValidationError(
            f"{path} must be a finite non-negative number"
            if not allow_negative
            else f"{path} must be a finite number"
        )
    if not allow_negative and value < 0:
        raise ValidationError(f"{path} must be a finite non-negative number")
    return value


def _validate_non_empty_string_list(
    values: list[Any],
    path: str,
    *,
    allow_empty_list: bool,
) -> None:
    if not values and not allow_empty_list:
        raise ValidationError(f"{path} must not be empty")
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str):
            raise ValidationError(f"{item_path} must be a non-empty string")
        if not item.strip():
            raise ValidationError(f"{item_path} must be a non-empty string")


def _validate_metric_name_list(values: list[Any], path: str, registered: set[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{item_path} must be a non-empty string")
        if item not in registered:
            raise ValidationError(f"{path} contains unknown metric: {item}")
        if item in seen:
            raise ValidationError(f"{path} contains duplicate metric: {item}")
        seen.add(item)


def _validate_entity(entity: Any, path: str) -> None:
    if entity is None:
        raise ValidationError(f"{path} must be a non-empty string or object with name/entity/symbol")
    if isinstance(entity, str):
        if not entity.strip():
            raise ValidationError(f"{path} must be a non-empty string or object with name/entity/symbol")
        return
    if isinstance(entity, dict):
        name = entity.get("name") or entity.get("entity") or entity.get("symbol")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(f"{path} must be a non-empty string or object with name/entity/symbol")
        return
    raise ValidationError(f"{path} must be a non-empty string or object with name/entity/symbol")


def _validate_step(step: Any, path: str) -> None:
    if not isinstance(step, dict):
        raise ValidationError(f"{path} must be an object")
    name = step.get("name") or step.get("step")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(f"{path}.name must be a non-empty string")
    if "status" in step and step["status"] is not None and not isinstance(step["status"], str):
        raise ValidationError(f"{path}.status must be a string")


def _validate_metric(metric: Any, path: str) -> None:
    if not isinstance(metric, dict):
        raise ValidationError(f"{path} must be an object")
    for field_name in ("entity", "name", "period", "formula", "unit", "currency", "source"):
        if field_name in metric:
            _validate_optional_string(metric[field_name], f"{path}.{field_name}")
    if "value" in metric and metric["value"] is not None:
        _require_finite_number(metric["value"], f"{path}.value", allow_negative=True)
    if "inputs" in metric:
        inputs = metric["inputs"]
        if not isinstance(inputs, dict):
            raise ValidationError(f"{path}.inputs must be an object")
        for key, raw in inputs.items():
            input_path = f"{path}.inputs.{key}"
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(f"{path}.inputs keys must be non-empty strings")
            _validate_metric_input(raw, input_path)


def _validate_metric_input(raw: Any, path: str) -> None:
    # Compatibility: legacy fixtures use bare numbers; LumenFin exports input objects.
    if isinstance(raw, dict):
        if "value" not in raw:
            raise ValidationError(f"{path}.value is required when input is an object")
        _require_finite_number(raw["value"], f"{path}.value", allow_negative=True)
        for field_name in ("unit", "currency", "period", "source", "citation", "source_record_id"):
            if field_name in raw:
                _validate_optional_string(raw[field_name], f"{path}.{field_name}")
        return
    _require_finite_number(raw, path, allow_negative=True)


def _validate_evidence(item: Any, path: str) -> None:
    if not isinstance(item, dict):
        raise ValidationError(f"{path} must be an object")
    for field_name in (
        "entity",
        "citation",
        "period",
        "text",
        "source_type",
        "provider",
        "source_record_id",
    ):
        if field_name in item:
            _validate_optional_string(item[field_name], f"{path}.{field_name}")


def _validate_market_data(item: Any, path: str) -> None:
    if not isinstance(item, dict):
        raise ValidationError(f"{path} must be an object")
    for field_name in ("entity", "status", "provider", "error", "as_of"):
        if field_name in item:
            _validate_optional_string(item[field_name], f"{path}.{field_name}")


def _validate_claim(claim: Any, path: str) -> None:
    if not isinstance(claim, dict):
        raise ValidationError(f"{path} must be an object")
    for field_name in (
        "entity",
        "metric_name",
        "period",
        "unit",
        "citation",
        "evidence_id",
        "claim_id",
        "claim_type",
        "statement",
        "verification",
        "verify_reason",
    ):
        if field_name in claim:
            _validate_optional_string(claim[field_name], f"{path}.{field_name}")
    if "value" in claim and claim["value"] is not None:
        value = claim["value"]
        if isinstance(value, str):
            if not value.strip():
                raise ValidationError(f"{path}.value must be a finite number or non-empty string")
        else:
            _require_finite_number(value, f"{path}.value", allow_negative=True)
    if "verified" in claim and not isinstance(claim["verified"], bool):
        raise ValidationError(f"{path}.verified must be a boolean")
    if "evidence_refs" in claim:
        if not isinstance(claim["evidence_refs"], list):
            raise ValidationError(f"{path}.evidence_refs must be a list")
        for index, ref in enumerate(claim["evidence_refs"]):
            if not isinstance(ref, dict):
                raise ValidationError(f"{path}.evidence_refs[{index}] must be an object")


def _validate_optional_string(value: Any, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValidationError(f"{path} must be a string")
