from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def retrieval_provenance(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    if not case.get("require_retrieval_provenance"):
        return MetricResult("retrieval_provenance", 100.0, True, [])

    metadata = run.get("metadata") or {}
    provenance_by_entity = metadata.get("retrieval_provenance") or {}
    if not provenance_by_entity:
        provenance_by_entity = _derive_from_entities(run)

    expected_entities = [str(name) for name in case.get("expected_entities") or []]
    forbidden_sources = {str(item) for item in case.get("forbidden_structured_sources") or ["none"]}
    min_confidence = float(case.get("min_retrieval_confidence", 0.35))
    data_mode = str(metadata.get("data_mode") or case.get("data_mode") or "demo")

    findings: list[Finding] = []
    checked = 0

    for entity in expected_entities:
        checked += 1
        record = provenance_by_entity.get(entity) or {}
        structured_source = str(record.get("structured_source") or "none")
        if structured_source in forbidden_sources:
            findings.append(
                Finding(
                    metric="retrieval_provenance",
                    severity="high",
                    message=(
                        f"{entity} structured_source={structured_source} is not allowed "
                        f"for data_mode={data_mode}."
                    ),
                    recommendation="Upload source documents or enable verified structured data before export.",
                    action="retrieve",
                    target={"entity": entity, "structured_source": structured_source},
                )
            )
            continue

        confidence = _entity_confidence(run, entity)
        if data_mode == "live" and confidence is not None and confidence < min_confidence:
            findings.append(
                Finding(
                    metric="retrieval_provenance",
                    severity="medium",
                    message=(
                        f"{entity} retrieval confidence {confidence:.2f} is below live threshold "
                        f"{min_confidence:.2f}."
                    ),
                    recommendation="Improve retrieval coverage (RAG hits, market API, PDF extraction) before gating.",
                    action="retrieve",
                    target={"entity": entity, "confidence": confidence},
                )
            )

    if checked == 0:
        return MetricResult(
            "retrieval_provenance",
            0.0,
            False,
            [
                Finding(
                    metric="retrieval_provenance",
                    severity="high",
                    message="Case requires retrieval provenance but no expected entities were configured.",
                    recommendation="Set expected_entities in the diligence case.",
                )
            ],
        )

    score = round((checked - len(findings)) / checked * 100, 2)
    return MetricResult("retrieval_provenance", score, not findings, findings)


def _derive_from_entities(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    derived: dict[str, dict[str, Any]] = {}
    for metric in run.get("metrics") or []:
        entity = str(metric.get("entity") or "")
        if not entity or entity in derived:
            continue
        confidence = metric.get("confidence") or {}
        if confidence.get("structured_source"):
            derived[entity] = {
                "structured_source": confidence.get("structured_source"),
                "data_mode": confidence.get("data_mode"),
                "market_status": confidence.get("market_status"),
            }
    return derived


def _entity_confidence(run: dict[str, Any], entity: str) -> float | None:
    for metric in run.get("metrics") or []:
        if str(metric.get("entity")) != entity:
            continue
        confidence = metric.get("confidence") or {}
        value = confidence.get("retrieval_overall")
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None
