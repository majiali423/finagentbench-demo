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


def entity_leakage(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    """Fail when forbidden peers/customers appear in the run entity list.

    Use with fixed ``expected_entities`` / ``forbidden_entities`` on issuer filings.
    Compare intents should omit leaked peers from ``forbidden_entities`` (or leave empty).
    """
    forbidden = {_entity_name(item) for item in case.get("forbidden_entities") or []}
    forbidden.discard("")
    if not forbidden:
        return MetricResult("entity_leakage", 100.0, True, [])

    actual = {_entity_name(entity) for entity in run.get("entities", [])}
    actual.discard("")
    leaked = sorted(actual & forbidden)
    findings = [
        Finding(
            metric="entity_leakage",
            severity="high",
            message=f"Forbidden entity leaked into live scope: {entity}",
            recommendation=(
                "Keep document body mentions out of issuer live-lookup scope; "
                "only allow peers when the user explicitly requests a comparison."
            ),
            action="replan",
            target={"entity": entity},
        )
        for entity in leaked
    ]
    score = 100.0 if not leaked else round(max(0.0, 100.0 - 25.0 * len(leaked)), 2)
    return MetricResult("entity_leakage", score, not findings, findings)


def _entity_name(entity: Any) -> str:
    if isinstance(entity, str):
        return entity
    if isinstance(entity, dict):
        return str(entity.get("name") or entity.get("entity") or entity.get("symbol") or "")
    return str(entity)
