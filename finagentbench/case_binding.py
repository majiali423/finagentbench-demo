from __future__ import annotations

from typing import Any


def resolve_case_for_run(run: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Bind case expectations that should come from the run (e.g. entities).

    When ``derive_entities_from_run`` is true, expected_entities are taken from
    the exported FinRun so one generic case can gate arbitrary LumenFin queries.
    This is only valid for ``case_mode=compatibility`` (smoke / schema gates).
    ``forbidden_entities`` are never overwritten by derivation.
    """
    resolved = dict(case)
    if "forbidden_entities" not in resolved:
        resolved["forbidden_entities"] = []
    if resolved.get("derive_entities_from_run"):
        mode = str(resolved.get("case_mode") or "quality")
        allow_derived = bool(resolved.get("allow_derived_expectations"))
        if mode != "compatibility" and not allow_derived:
            # Defensive: validate_case should already reject this combination.
            raise ValueError(
                "derive_entities_from_run requires case_mode=compatibility "
                "or allow_derived_expectations=true"
            )
        entities = [_entity_name(item) for item in run.get("entities") or []]
        resolved["expected_entities"] = [name for name in entities if name]
        if not resolved["expected_entities"] and resolved.get("companies"):
            resolved["expected_entities"] = [str(name) for name in resolved["companies"] if name]
    return resolved


def _entity_name(entity: Any) -> str:
    if isinstance(entity, str):
        return entity
    if isinstance(entity, dict):
        return str(entity.get("name") or entity.get("entity") or entity.get("symbol") or "")
    return str(entity)
