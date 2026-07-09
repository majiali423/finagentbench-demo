from __future__ import annotations

import copy
from typing import Any


SEMANTIC_METRICS = {"evidence_support", "risk_quality", "compliance_semantic"}


def apply_profile(case: dict[str, Any], profile: str) -> dict[str, Any]:
    profile = profile.lower()
    if profile == "default":
        return case
    if profile not in {"ci", "audit"}:
        raise ValueError(f"Unknown profile: {profile}")

    profiled = copy.deepcopy(case)
    enabled = profiled.get("enabled_metrics")
    if profile == "ci":
        if enabled:
            profiled["enabled_metrics"] = [
                metric for metric in enabled
                if metric not in SEMANTIC_METRICS
            ]
        profiled["semantic_profile"] = "ci"
        return profiled

    audit_metrics = profiled.get("audit_metrics", [])
    if audit_metrics:
        merged = list(enabled or [])
        for metric in audit_metrics:
            if metric not in merged:
                merged.append(metric)
        profiled["enabled_metrics"] = merged
    profiled["semantic_profile"] = "audit"
    return profiled
