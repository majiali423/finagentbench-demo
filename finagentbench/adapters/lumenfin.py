"""LumenFin state → canonical FinRun adapter.

Maps exported LumenFin ``*_state.json`` into the neutral FinRun schema used by
FinAgentBench evaluators. Fundamentals use period-agnostic keys (``revenue``)
with legacy ``revenue_2025`` accepted for older fixtures — never hard-require
year-suffixed field names.
"""

from __future__ import annotations

import re
from typing import Any

from ..schema import FINRUN_SCHEMA_VERSION

FORMULA_BY_METRIC = {
    "ebitda_margin": ("ebitda / revenue", {"ebitda": "ebitda", "revenue": "revenue"}),
    "r_and_d_intensity": ("r_and_d / revenue", {"r_and_d": "r_and_d", "revenue": "revenue"}),
    "operating_margin": (
        "operating_income / revenue",
        {"operating_income": "operating_income", "revenue": "revenue"},
    ),
}

_CANONICAL = ("revenue", "ebitda", "r_and_d", "operating_income", "subsidiary_revenue")
_LEGACY = {
    "revenue_2025": "revenue",
    "ebitda_2025": "ebitda",
    "r_and_d_2025": "r_and_d",
    "operating_income_2025": "operating_income",
    "subsidiary_revenue_2025": "subsidiary_revenue",
}
_PERIOD_SUFFIX_RE = re.compile(
    r"^(?P<base>revenue|ebitda|r_and_d|operating_income|subsidiary_revenue)_(?P<year>20\d{2})$"
)


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
            "schema_version": FINRUN_SCHEMA_VERSION,
            "run_id": str(payload.get("run_id") or payload.get("thread_id") or "lumenfin-run"),
            "query": str(payload.get("query") or ""),
            "metadata": {
                "adapter": self.name,
                "source_project": "lumenfin-agent",
                "thread_id": payload.get("thread_id"),
                "workflow_status": payload.get("workflow_status"),
                "llm_backend": payload.get("llm_backend"),
                "data_mode": payload.get("data_mode"),
                "input_guardrail_summary": payload.get("input_guardrail_summary") or {},
                "input_guardrail_findings": payload.get("input_guardrail_findings") or [],
                "compliance_violations": payload.get("compliance_violations") or [],
                "retrieval_provenance": _retrieval_provenance(payload),
            },
            "entities": [{"name": company} for company in _companies(payload)],
            "steps": _steps(payload),
            "metrics": _metrics(payload),
            "evidence": _evidence(payload),
            "market_data": _market_data(payload),
            "final_output": str(payload.get("final_report") or ""),
        }


def _canonical_name(key: str) -> str | None:
    if key in _CANONICAL:
        return key
    if key in _LEGACY:
        return _LEGACY[key]
    match = _PERIOD_SUFFIX_RE.match(key)
    return match.group("base") if match else None


def get_fundamental(market_data: dict[str, Any] | None, name: str) -> float | None:
    """Read a fundamental accepting canonical or legacy/period-suffixed keys."""
    data = market_data or {}
    canonical = _canonical_name(name) or name
    candidates = [canonical, f"{canonical}_2025"]
    for key, value in data.items():
        mapped = _canonical_name(str(key))
        if mapped == canonical:
            candidates.append(str(key))
    seen: set[str] = set()
    for key in candidates:
        if key in seen:
            continue
        seen.add(key)
        if key not in data:
            continue
        value = data.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def period_label_from_meta(meta: dict[str, Any] | None, *, default: str = "latest") -> str:
    meta = meta or {}
    for key in ("fiscal_year", "period", "fy", "period_end"):
        value = meta.get(key)
        if value in (None, ""):
            continue
        text = str(value)
        if key == "fiscal_year" or (key == "fy" and text.isdigit()):
            return f"FY{text}"
        if re.fullmatch(r"20\d{2}", text):
            return f"FY{text}"
        return text
    return default


def _companies(payload: dict[str, Any]) -> list[str]:
    return [str(company) for company in payload.get("companies") or []]


def _retrieval_provenance(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    explicit = payload.get("retrieval_provenance") or {}
    if explicit:
        return {str(company): dict(value) for company, value in explicit.items()}

    derived: dict[str, dict[str, Any]] = {}
    for company, bundle in (payload.get("retrieved_docs") or {}).items():
        provenance = bundle.get("provenance")
        if isinstance(provenance, dict):
            derived[str(company)] = dict(provenance)
            continue
        structured_source = str(bundle.get("structured_source") or "none")
        derived[str(company)] = {"structured_source": structured_source}
    return derived


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
        bundle = retrieved_docs.get(company) or {}
        source_values = bundle.get("market_data") or {}
        period = period_label_from_meta(bundle.get("fundamentals_meta"))
        source = str(
            (bundle.get("provenance") or {}).get("structured_source")
            or bundle.get("structured_source")
            or "unknown"
        )
        for name, value in metrics.items():
            formula, input_map = FORMULA_BY_METRIC.get(name, ("", {}))
            inputs = _metric_inputs(input_map, source_values, period=period)
            item = {
                "entity": str(company),
                "name": str(name),
                "period": period,
                "value": value,
                "unit": "ratio" if formula else "",
                "source": source,
                "formula": formula,
                "inputs": inputs,
                "confidence": _metric_confidence(
                    metric_confidence.get(company) or {},
                    name,
                    bundle,
                ),
            }
            output.append(item)
    return output


def _metric_inputs(
    input_map: dict[str, str],
    source_values: dict[str, Any],
    *,
    period: str,
) -> dict[str, Any]:
    inputs = {}
    for input_name, source_key in input_map.items():
        value = get_fundamental(source_values, source_key)
        if value is None:
            continue
        inputs[input_name] = {
            "value": value,
            "unit": "billion",
            "currency": "USD",
            "period": period,
            "source": "market_data",
        }
    return inputs


def _metric_confidence(
    company_confidence: dict[str, Any],
    metric_name: str,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    confidence = dict(company_confidence.get(metric_name) or {})
    provenance = bundle.get("provenance") or {}
    if provenance:
        confidence.setdefault("structured_source", provenance.get("structured_source"))
        confidence.setdefault("data_mode", provenance.get("data_mode"))
        confidence.setdefault("market_status", provenance.get("market_status"))
    retrieval_confidence = bundle.get("confidence") or {}
    if retrieval_confidence:
        confidence.setdefault("retrieval_overall", retrieval_confidence.get("overall"))
    return confidence


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
                citation=str(
                    hit.get("citation") or hit.get("source") or hit.get("filename") or f"rag:{company}:{index}"
                ),
                source_type=str(hit.get("source_type") or "rag"),
                text=str(hit.get("text") or hit.get("snippet") or hit.get("excerpt") or ""),
                period=str(hit.get("period") or "latest"),
            )

    for company, bundle in retrieved_docs.items():
        period = period_label_from_meta(bundle.get("fundamentals_meta"))
        for index, doc in enumerate(bundle.get("source_documents") or []):
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=str(
                    doc.get("citation")
                    or doc.get("filename")
                    or doc.get("source")
                    or f"source:{company}:{index}"
                ),
                source_type=str(doc.get("source_type") or "document"),
                text=str(doc.get("excerpt") or doc.get("text") or ""),
                period=period,
            )
        supply_chain = bundle.get("supply_chain") or {}
        if supply_chain:
            signals = [str(signal) for signal in supply_chain.get("signals") or []]
            text = (
                f"{company} supply chain risk level is {supply_chain.get('risk_level', 'unknown')}. "
                f"Signals: {'; '.join(signals)}"
            )
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:supply_chain:{company}:{period}",
                source_type="sample_db",
                text=text,
                period=period,
            )
        quotes = [str(quote) for quote in bundle.get("earnings_call_quotes") or []]
        if quotes:
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:earnings_call_quotes:{company}:{period}",
                source_type="sample_db",
                text=f"{company} management commentary: {'; '.join(quotes)}",
                period=period,
            )
        market_data = bundle.get("market_data") or {}
        if market_data:
            text = (
                f"{company} {period} revenue was {get_fundamental(market_data, 'revenue')} billion USD, "
                f"EBITDA was {get_fundamental(market_data, 'ebitda')} billion USD, "
                f"R&D was {get_fundamental(market_data, 'r_and_d')} billion USD, and "
                f"operating income was {get_fundamental(market_data, 'operating_income')} billion USD."
            )
            source = str(bundle.get("structured_source") or "fundamentals")
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:{source}:{company}:{period}",
                source_type="fundamentals" if source != "sample_db" else "sample_db",
                text=text,
                period=period,
            )
    for company, scores in (payload.get("risk_scores") or {}).items():
        if not isinstance(scores, dict):
            continue
        parts = [
            f"{name}={value}"
            for name, value in scores.items()
            if isinstance(value, (int, float))
        ]
        if parts:
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:risk_model:{company}:model",
                source_type="risk_model",
                text=(
                    f"{company} model-derived risk scores are screening indicators, not standalone cited facts: "
                    + ", ".join(parts)
                    + "."
                ),
                period="model",
            )
    for company, snapshot in (payload.get("market_snapshots") or {}).items():
        if snapshot.get("current_price") is None:
            continue
        details = []
        for key in ("current_price", "trailing_pe", "monthly_return", "fifty_two_week_high", "fifty_two_week_low"):
            if snapshot.get(key) is not None:
                details.append(f"{key}={snapshot.get(key)}")
        if details:
            _append_evidence(
                evidence,
                seen,
                company=str(company),
                citation=f"lumenfin:market_snapshot:{company}:{snapshot.get('fetched_at') or 'latest'}",
                source_type="market_data",
                text=(
                    f"{company} live market snapshot from {snapshot.get('provider') or 'unknown'} "
                    f"as_of={snapshot.get('fetched_at') or 'n/a'}: "
                    + ", ".join(details)
                    + "."
                ),
                period="latest",
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
    period: str | None = None,
) -> None:
    key = (company, citation)
    if key in seen:
        return
    seen.add(key)
    evidence.append(
        {
            "entity": company,
            "citation": citation,
            "period": period or "latest",
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
                "status": str(
                    snapshot.get("status")
                    or ("ok" if snapshot.get("current_price") is not None else "failed")
                ),
                "provider": snapshot.get("provider") or "",
                "as_of": snapshot.get("fetched_at") or snapshot.get("as_of") or "",
                "error": snapshot.get("error") or "",
                "current_price": snapshot.get("current_price"),
                "trailing_pe": snapshot.get("trailing_pe"),
                "monthly_return": snapshot.get("monthly_return"),
                "fifty_two_week_high": snapshot.get("fifty_two_week_high"),
                "fifty_two_week_low": snapshot.get("fifty_two_week_low"),
            }
        )
    return output
