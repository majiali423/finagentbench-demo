from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def market_data_disclosure(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    output = (run.get("final_output") or "").lower()
    failed = [
        item
        for item in run.get("market_data", [])
        if str(item.get("status", "")).lower() not in {"ok", "cached", "stale"}
    ]
    findings: list[Finding] = []
    for item in failed:
        entity = str(item.get("entity", "unknown"))
        disclosed = entity.lower() in output and any(
            token in output
            for token in ("failed", "unavailable", "missing", "not available")
        )
        if not disclosed:
            findings.append(
                Finding(
                    metric="market_data_disclosure",
                    severity="medium",
                    message=f"Market data failed for {entity} but final output did not disclose it.",
                    recommendation="Disclose per-entity market data failures in the methodology or data sources section.",
                )
            )
    score = 100.0 if not failed else round((len(failed) - len(findings)) / len(failed) * 100, 2)
    return MetricResult("market_data_disclosure", score, not findings, findings)
