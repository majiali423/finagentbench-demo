from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def entity_coverage(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    expected = set(case.get("expected_entities", []))
    actual = {_entity_name(entity) for entity in run.get("entities", [])}
    actual.discard("")
    missing = sorted(expected - actual)
    findings = [
        Finding(
            metric="entity_coverage",
            severity="high",
            message=f"Missing expected entity: {entity}",
            recommendation="Check entity extraction/planning for comparative queries.",
        )
        for entity in missing
    ]
    score = 100.0 if not expected else round((len(expected) - len(missing)) / len(expected) * 100, 2)
    return MetricResult("entity_coverage", score, not findings, findings)


def _entity_name(entity: Any) -> str:
    if isinstance(entity, str):
        return entity
    if isinstance(entity, dict):
        return str(entity.get("name") or entity.get("entity") or entity.get("symbol") or "")
    return str(entity)
