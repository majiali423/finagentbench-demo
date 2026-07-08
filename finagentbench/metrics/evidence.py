from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def evidence_coverage(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    expected_entities = set(case.get("expected_entities", []))
    evidence_by_entity = {}
    for item in run.get("evidence", []):
        entity = item.get("entity")
        if entity and item.get("citation"):
            evidence_by_entity.setdefault(entity, 0)
            evidence_by_entity[entity] += 1
    missing = sorted(entity for entity in expected_entities if evidence_by_entity.get(entity, 0) == 0)
    findings = [
        Finding(
            metric="evidence_coverage",
            severity="high",
            message=f"No cited evidence found for entity: {entity}",
            recommendation="Attach source citations or retrieved evidence snippets for each analyzed entity.",
        )
        for entity in missing
    ]
    score = 100.0 if not expected_entities else round((len(expected_entities) - len(missing)) / len(expected_entities) * 100, 2)
    return MetricResult("evidence_coverage", score, not findings, findings)
