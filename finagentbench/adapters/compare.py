"""Normalized FinRun views for exporter/adapter schema comparison."""

from __future__ import annotations

from typing import Any


def _entity_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("name") or "")
    return str(item or "")


def comparable_finrun(run: dict[str, Any]) -> dict[str, Any]:
    """Stable subset used to compare two FinRun normalizers without requiring identical extras."""

    def _round(value: Any) -> float | None:
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            return None

    return {
        "run_id": str(run.get("run_id") or ""),
        "final_output": str(run.get("final_output") or ""),
        "entities": sorted(_entity_name(item) for item in run.get("entities") or []),
        "steps": [str(item.get("name") or "") for item in run.get("steps") or []],
        "metrics": sorted(
            (
                str(item.get("entity") or ""),
                str(item.get("name") or ""),
                str(item.get("period") or ""),
                _round(item.get("value")),
            )
            for item in run.get("metrics") or []
        ),
        "evidence_citations": sorted(
            str(item.get("citation") or "") for item in run.get("evidence") or [] if item.get("citation")
        ),
        "claim_entities": sorted(
            {
                str(item.get("entity") or "")
                for item in run.get("claims") or []
                if isinstance(item, dict) and item.get("entity")
            }
        ),
    }
