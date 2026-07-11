from __future__ import annotations

from typing import Any


FORMULA_BY_METRIC = {
    "ebitda_margin": ("ebitda / revenue", {"ebitda": "ebitda_2025", "revenue": "revenue_2025"}),
    "r_and_d_intensity": ("r_and_d / revenue", {"r_and_d": "r_and_d_2025", "revenue": "revenue_2025"}),
    "operating_margin": ("operating_income / revenue", {"operating_income": "operating_income_2025", "revenue": "revenue_2025"}),
}


class LumenFinAdapter:
    name = "lumenfin"

    def can_parse(self, payload: dict[str, Any]) -> bool:
        return (
            payload.get("llm_backend") is not None
            and "final_report" in payload
            and "audit_log" in payload
            and ("financial_metrics" in payload or "retrieved_docs" in payload)
        )

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(payload.get("run_id") or payload.get("thread_id") or "lumenfin-run"),
            "query": str(payload.get("query") or ""),
            "metadata": {
                "adapter": self.name,
                "source_project": "lumenfin-agent",
                "thread_id": payload.get("thread_id"),
                "workflow_status": payload.get("workflow_status"),
                "llm_backend": payload.get("llm_backend"),
            },
            "entities": [{"name": company} for company in _companies(payload)],
            "steps": _steps(payload),
            "metrics": _metrics(payload),
            "evidence": _evidence(payload),
            "market_data": _market_data(payload),
            "final_output": str(payload.get("final_report") or ""),
        }


def _companies(payload: dict[str, Any]) -> list[str]:
    return [str(company) for company in payload.get("companies") or []]


def _steps(payload: dict[str, Any]) -> list[dict[str, str]]:
    steps = []
    for event in payload.get("audit_log") or []:
        name = event.get("step")
        if name:
            steps.append({"name": str(name), "status": str(event.get("status") or "ok")})
    return steps


def _metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    financial_metrics = payload.get("financial_metrics") or {}
    retrieved_docs = payload.get("retrieved_docs") or {}
    metric_confidence = payload.get("metric_confidence") or {}
    for company, metrics in financial_metrics.items():
        source_values = (retrieved_docs.get(company) or {}).get("market_data") or {}
        for name, value in metrics.items():
            formula, input_map = FORMULA_BY_METRIC.get(name, ("", {}))
            output.append(
                {
                    "entity": str(company),
                    "name": str(name),
                    "period": "FY2025",
                    "value": value,
                    "formula": formula,
                    "inputs": _metric_inputs(input_map, source_values),
                    "confidence": (metric_confidence.get(company) or {}).get(name, {}),
                }
            )
    return output


def _metric_inputs(input_map: dict[str, str], source_values: dict[str, Any]) -> dict[str, Any]:
    inputs = {}
    for input_name, source_key in input_map.items():
        if source_key in source_values:
            inputs[input_name] = {
                "value": source_values[source_key],
                "unit": "billion",
                "currency": "USD",
                "period": "FY2025",
            }
    return inputs


def _evidence(payload: dict[str, Any]) -> list[dict[str, str]]:
    evidence = []
    seen = set()
    retrieved_docs = payload.get("retrieved_docs") or {}
    rag_evidence = payload.get("rag_evidence") or {}

    for company, hits in rag_evidence.items():
        for index, hit in enumerate(hits):
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=str(hit.get("citation") or hit.get("source") or hit.get("filename") or f"rag:{company}:{index}"),
                source_type=str(hit.get("source_type") or "rag"),
                text=str(hit.get("text") or hit.get("snippet") or hit.get("excerpt") or ""),
            )

    for company, bundle in retrieved_docs.items():
        for index, doc in enumerate(bundle.get("source_documents") or []):
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=str(doc.get("citation") or doc.get("filename") or doc.get("source") or f"source:{company}:{index}"),
                source_type=str(doc.get("source_type") or "document"),
                text=str(doc.get("excerpt") or doc.get("text") or ""),
            )
        market_data = bundle.get("market_data") or {}
        if market_data:
            text = (
                f"{company} FY2025 revenue was {market_data.get('revenue_2025')} billion USD, "
                f"EBITDA was {market_data.get('ebitda_2025')} billion USD, "
                f"R&D was {market_data.get('r_and_d_2025')} billion USD, and "
                f"operating income was {market_data.get('operating_income_2025')} billion USD."
            )
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:sample_financial_data:{company}:FY2025",
                source_type="sample_db",
                text=text,
            )
    return evidence


def _append_evidence(
    evidence: list[dict[str, str]],
    seen: set[tuple[str, str]],
    *,
    company: str,
    citation: str,
    source_type: str,
    text: str,
) -> None:
    key = (company, citation)
    if key in seen:
        return
    seen.add(key)
    evidence.append(
        {
            "entity": company,
            "citation": citation,
            "period": "FY2025",
            "source_type": source_type,
            "provider": "lumenfin",
            "text": text,
        }
    )


def _market_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for company, snapshot in (payload.get("market_snapshots") or {}).items():
        output.append(
            {
                "entity": str(company),
                "status": str(snapshot.get("status") or ("ok" if snapshot.get("current_price") is not None else "failed")),
                "provider": snapshot.get("provider") or "",
                "as_of": snapshot.get("fetched_at") or snapshot.get("as_of") or "",
                "error": snapshot.get("error") or "",
            }
        )
    return output
