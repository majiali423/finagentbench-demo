from __future__ import annotations

from typing import Any


class DueDiligenceAdapter:
    name = "due-diligence"

    def can_parse(self, payload: dict[str, Any]) -> bool:
        return "report_markdown" in payload and (
            "computed_ratios" in payload or "workflow_events" in payload
        )

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = payload.get("company_name") or payload.get("target") or "unknown"
        return {
            "run_id": str(payload.get("run_id") or "due-diligence-run"),
            "query": payload.get("query", ""),
            "metadata": {"adapter": self.name, **dict(payload.get("metadata", {}))},
            "entities": [{"name": str(target)}],
            "steps": _steps(payload.get("workflow_events", [])),
            "metrics": _metrics(str(target), payload.get("computed_ratios", [])),
            "evidence": _evidence(str(target), payload.get("source_snippets", [])),
            "market_data": _market_data(str(target), payload.get("market_quotes", [])),
            "final_output": payload.get("report_markdown", ""),
        }


def _steps(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    steps = []
    for event in events:
        name = event.get("step") or event.get("name")
        if name:
            steps.append({"name": str(name), "status": str(event.get("status", "ok"))})
    return steps


def _metrics(default_entity: str, ratios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = []
    for ratio in ratios:
        metrics.append(
            {
                "entity": str(ratio.get("entity") or default_entity),
                "name": str(ratio.get("name") or ratio.get("metric")),
                "period": ratio.get("period"),
                "value": ratio.get("value"),
                "formula": ratio.get("formula"),
                "inputs": ratio.get("inputs", {}),
            }
        )
    return metrics


def _evidence(default_entity: str, snippets: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence = []
    for snippet in snippets:
        citation = snippet.get("citation") or snippet.get("source")
        if citation:
            evidence.append(
                {
                    "entity": str(snippet.get("entity") or default_entity),
                    "citation": str(citation),
                    "period": str(snippet.get("period") or ""),
                    "source_type": str(snippet.get("source_type") or ""),
                    "provider": str(snippet.get("provider") or ""),
                    "text": str(snippet.get("text") or ""),
                }
            )
    return evidence


def _market_data(default_entity: str, quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    market_data = []
    for quote in quotes:
        market_data.append(
            {
                "entity": str(quote.get("entity") or default_entity),
                "status": str(quote.get("status", "ok")),
                "provider": quote.get("provider", ""),
                "as_of": quote.get("as_of", ""),
                "error": quote.get("error", ""),
            }
        )
    return market_data
