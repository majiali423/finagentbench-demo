from __future__ import annotations

import hashlib
import json
from importlib import metadata
from typing import Any

from .metrics.registry import resolve_metrics
from .schema import EvalReport


def tool_version() -> str:
    try:
        return metadata.version("finagentbench")
    except metadata.PackageNotFoundError:
        return "0.1.0-dev"


def case_hash(case: dict[str, Any]) -> str:
    encoded = json.dumps(case, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def attach_provenance(
    report: EvalReport,
    case: dict[str, Any],
    *,
    profile: str = "default",
    adapter: str = "auto",
) -> EvalReport:
    enabled = [metric.__name__ for metric in resolve_metrics(case)]
    return EvalReport(
        run_id=report.run_id,
        score=report.score,
        passed=report.passed,
        metrics=report.metrics,
        tool_version=tool_version(),
        case_id=str(case.get("id") or ""),
        case_hash=case_hash(case),
        profile=profile,
        adapter=adapter,
        enabled_metrics=enabled,
    )
