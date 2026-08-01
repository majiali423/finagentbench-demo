from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult

_FACTUAL_PERIOD_SOURCES = {
    "sec_companyfacts", "provider_record", "document_text", "table_header",
    "structured_table", "filing_fact",
}
_ASSUMED_ALIGNMENTS = {
    "assumed_from_query", "fallback_latest", "upload_labeled", "unspecified", "unknown",
}


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

        if case.get("require_factual_period_provenance"):
            findings.extend(_period_provenance_findings(run, entity))

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

    score = round(max(0.0, (checked - len(findings)) / checked * 100), 2)
    return MetricResult("retrieval_provenance", score, not findings, findings)


def _period_provenance_findings(run: dict[str, Any], entity: str) -> list[Finding]:
    findings: list[Finding] = []
    for metric in run.get("metrics") or []:
        if str(metric.get("entity") or "") != entity or not metric.get("formula"):
            continue
        periods: set[str] = set()
        for input_name, raw in (metric.get("inputs") or {}).items():
            record = raw if isinstance(raw, dict) else {}
            period = str(record.get("period") or "").strip()
            period_source = str(record.get("period_source") or "").strip().casefold()
            alignment = str(record.get("period_alignment") or "").strip().casefold()
            record_proof = bool(
                str(record.get("citation") or "").strip()
                or str(record.get("source_record_id") or "").strip()
            )
            reason = None
            if not period:
                reason = "period missing"
            elif period_source not in _FACTUAL_PERIOD_SOURCES:
                reason = f"non-factual period_source={period_source or 'missing'}"
            elif alignment in _ASSUMED_ALIGNMENTS or not alignment:
                reason = f"non-exact period_alignment={alignment or 'missing'}"
            elif not record_proof:
                reason = "citation/source_record_id missing"
            if reason:
                findings.append(_period_finding(entity, metric, str(input_name), reason))
            else:
                periods.add(period)
        metric_period = str(metric.get("period") or "").strip()
        if len(periods) > 1 or (periods and metric_period not in periods):
            findings.append(
                _period_finding(
                    entity, metric, "formula", f"formula periods disagree: {sorted(periods)}"
                )
            )
    return findings


def _period_finding(
    entity: str, metric: dict[str, Any], input_name: str, reason: str
) -> Finding:
    return Finding(
        metric="retrieval_provenance",
        severity="high",
        message=(
            f"{entity} {metric.get('name')} input {input_name} has invalid period provenance: "
            f"{reason}."
        ),
        recommendation="Export factual per-metric period provenance and an auditable source record.",
        action="retrieve",
        target={"entity": entity, "metric": metric.get("name"), "input": input_name},
    )


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
