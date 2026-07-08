from __future__ import annotations

from typing import Any


class LumenFinAdapter:
    name = "lumenfin"

    def can_parse(self, payload: dict[str, Any]) -> bool:
        return "final_report" in payload or "financial_metrics" in payload or "audit_log" in payload

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(payload.get("run_id") or payload.get("thread_id") or "lumenfin-run"),
            "query": payload.get("query", ""),
            "entities": _entities(payload),
            "steps": _steps(payload.get("audit_log", [])),
            "metrics": _metrics(payload.get("financial_metrics", [])),
            "evidence": _evidence(payload.get("rag_evidence", [])),
            "market_data": _market_data(payload.get("market_snapshots", [])),
            "final_output": payload.get("final_report", ""),
        }


def _entities(payload: dict[str, Any]) -> list[dict[str, str]]:
    companies = payload.get("companies") or payload.get("entities") or []
    return [{"name": str(company)} if isinstance(company, str) else dict(company) for company in companies]


def _steps(audit_log: list[dict[str, Any]]) -> list[dict[str, str]]:
    steps = []
    for event in audit_log:
        name = event.get("step") or event.get("name")
        if name:
            steps.append({"name": str(name), "status": str(event.get("status", "completed"))})
    return steps


def _metrics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = []
    for item in items:
        company = item.get("company") or item.get("entity")
        metric_name = item.get("metric") or item.get("name")
        if not company or not metric_name:
            continue
        metrics.append(
            {
                "entity": str(company),
                "name": str(metric_name),
                "value": item.get("value"),
                "formula": item.get("formula"),
                "inputs": item.get("inputs", {}),
            }
        )
    return metrics


def _evidence(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence = []
    for item in items:
        entity = item.get("company") or item.get("entity")
        citation = item.get("citation") or item.get("source") or item.get("url")
        if entity and citation:
            evidence.append(
                {
                    "entity": str(entity),
                    "citation": str(citation),
                    "text": str(item.get("text") or item.get("snippet") or ""),
                }
            )
    return evidence


def _market_data(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots = []
    for item in items:
        entity = item.get("company") or item.get("entity") or item.get("symbol")
        if entity:
            snapshots.append(
                {
                    "entity": str(entity),
                    "status": str(item.get("status", "ok")),
                    "error": item.get("error", ""),
                }
            )
    return snapshots
