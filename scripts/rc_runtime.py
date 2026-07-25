"""Side-effect-free helpers for RC validation.

Import of this module must not:
- load dotenv
- change process cwd
- construct LumenFin services
- open databases / Milvus
- call network providers
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def live_analyze(
    *,
    lumen_root: Path,
    out_dir: Path,
    query: str,
    docs: list[Path],
    prefix: str,
) -> tuple[dict[str, Any], float, str | None]:
    """Run one live LumenFin analyze call. Heavy imports are deferred."""
    from dataclasses import replace

    from lumenfin.config import AppConfig
    from lumenfin.service import LumenFinAnalysisService

    cfg = AppConfig.from_env()
    if not (cfg.llm.api_key or "").strip():
        raise RuntimeError("DEEPSEEK_API_KEY required")
    cfg = replace(
        cfg,
        data_mode="live",
        fetch_live_fundamentals=True,
        fetch_sec_fundamentals=True,
        rag_index_mode="sync_on_run",
        milvus_uri=str(out_dir / f"milvus_{uuid4().hex[:8]}.db"),
        milvus_isolate=True,
        output_dir=out_dir / "states",
    )
    service = LumenFinAnalysisService(cfg)
    thread_id = f"{prefix}-{uuid4().hex[:8]}"
    t0 = time.perf_counter()
    err = None
    state: dict[str, Any] = {}
    try:
        print(f"LIVE {thread_id} docs={[d.name for d in docs] or None}", flush=True)
        pkg = service.analyze(
            query=query,
            document_paths=[str(d) for d in docs] or None,
            thread_id=thread_id,
        )
        state = dict(pkg.get("result") or pkg)
        artifacts = pkg.get("artifacts") or {}
        sp = artifacts.get("state") or artifacts.get("state_path")
        if sp and Path(sp).exists():
            state = json.loads(Path(sp).read_text(encoding="utf-8"))
        else:
            matches = sorted(
                (lumen_root / "outputs").glob(f"{thread_id}*_state.json"),
                key=lambda p: p.stat().st_mtime,
            )
            alt = sorted(
                (out_dir / "states").glob(f"{thread_id}*_state.json"),
                key=lambda p: p.stat().st_mtime,
            )
            matches = matches or alt
            if matches:
                state = json.loads(matches[-1].read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        state = {
            "workflow_status": "crashed",
            "error": err,
            "traceback": traceback.format_exc()[-2000:],
        }
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    state.setdefault("thread_id", thread_id)
    return state, elapsed_ms, err


def export_finrun(state: dict[str, Any]) -> dict[str, Any]:
    from lumenfin.finrun import export_finrun_state

    run = export_finrun_state(state)
    for metric in run.get("metrics") or []:
        metric.setdefault("unit", "ratio" if metric.get("formula") else "")
        conf = metric.get("confidence") or {}
        metric.setdefault("source", conf.get("structured_source") or "unknown")
    return run


def evaluate_finrun(run: dict[str, Any], case_path: Path, out_dir: Path) -> dict[str, Any]:
    from finagentbench.profiles import apply_profile
    from finagentbench.provenance import attach_provenance
    from finagentbench.report import write_eval_report
    from finagentbench.runner import evaluate_run

    case = apply_profile(json.loads(case_path.read_text(encoding="utf-8")), "ci")
    report = attach_provenance(
        evaluate_run(run, case),
        case,
        profile="ci",
        adapter="lumenfin-export",
    )
    write_eval_report(report, out_dir)
    detail = {m.name: {"score": m.score, "passed": m.passed} for m in report.metrics}
    return {"score": report.score, "passed": report.passed, "metric_detail": detail}


def claim_coverage(state: dict[str, Any], final_output: str) -> dict[str, Any]:
    from lumenfin.claims import claims_from_state, filter_verified

    claims = claims_from_state(state)
    verified = filter_verified(claims)
    binding = state.get("claim_binding") or {}
    by_entity: dict[str, dict[str, int]] = {}
    for claim in verified:
        bucket = by_entity.setdefault(
            claim.entity, {"verified": 0, "numeric": 0, "risk": 0, "investment": 0}
        )
        bucket["verified"] += 1
        if claim.claim_type == "numeric":
            bucket["numeric"] += 1
        elif claim.claim_type == "risk_conclusion":
            bucket["risk"] += 1
        elif claim.claim_type == "investment_conclusion":
            bucket["investment"] += 1
    in_report = sum(
        1 for c in verified if c.primary_citation and c.primary_citation in final_output
    )
    companies = list(state.get("companies") or [])
    entities_with_numeric = sum(
        1 for e in companies if (by_entity.get(e) or {}).get("numeric", 0) > 0
    )
    return {
        "binding": binding,
        "verified_total": len(verified),
        "verified_in_report": in_report,
        "report_coverage": round(in_report / len(verified), 4) if verified else 0.0,
        "by_entity": by_entity,
        "entities_with_numeric_claims": entities_with_numeric,
        "entity_claim_coverage": (
            round(entities_with_numeric / len(companies), 4) if companies else 0.0
        ),
        "page_anchored": binding.get("page_anchored_verified", 0),
        "citation_markers": final_output.count("#p"),
    }


def judge_row(row: dict[str, Any]) -> dict[str, Any]:
    """Reliability judgments without changing FinAgentBench thresholds."""
    checks: list[dict[str, Any]] = []
    expect = row["expect"]
    status = row.get("workflow_status")
    crashed = status == "crashed" or bool(row.get("error"))

    checks.append({"name": "no_crash", "ok": not crashed, "detail": row.get("error") or "ok"})
    checks.append(
        {
            "name": "expected_workflow",
            "ok": status == expect,
            "detail": f"got={status} expect={expect}",
        }
    )

    cov = row.get("claim_coverage") or {}
    if expect == "completed":
        checks.append(
            {
                "name": "claim_coverage_min",
                "ok": (cov.get("verified_total") or 0) >= 3
                and (cov.get("report_coverage") or 0) >= 0.8,
                "detail": (
                    f"verified={cov.get('verified_total')} "
                    f"report_cov={cov.get('report_coverage')}"
                ),
            }
        )
        if row.get("scenario") == "multi_company":
            expect_ents = row.get("expect_entities") or []
            by_ent = cov.get("by_entity") or {}
            ok_ents = all((by_ent.get(e) or {}).get("numeric", 0) >= 1 for e in expect_ents)
            checks.append(
                {
                    "name": "per_entity_numeric_claims",
                    "ok": ok_ents,
                    "detail": str(by_ent),
                }
            )
            checks.append(
                {
                    "name": "entity_set",
                    "ok": set(expect_ents).issubset(set(row.get("entities") or [])),
                    "detail": f"entities={row.get('entities')}",
                }
            )
        if row.get("scenario") in {"long_document", "multi_metric"}:
            checks.append(
                {
                    "name": "long_or_metric_stability",
                    "ok": row.get("workflow_status") == "completed"
                    and (row.get("checkable") or 0) >= 1,
                    "detail": (
                        f"checkable={row.get('checkable')} "
                        f"markers={cov.get('citation_markers')}"
                    ),
                }
            )
        fab = row.get("fab") or {}
        if fab:
            detail = fab.get("metric_detail") or {}
            checks.append(
                {
                    "name": "fab_evidence_coverage",
                    "ok": (detail.get("evidence_coverage") or {}).get("score", 0) >= 100,
                    "detail": str((detail.get("evidence_coverage") or {}).get("score")),
                }
            )
            checks.append(
                {
                    "name": "fab_numeric",
                    "ok": (detail.get("numeric_correctness") or {}).get("score", 0) >= 80,
                    "detail": str((detail.get("numeric_correctness") or {}).get("score")),
                }
            )
            if row.get("scenario") != "multi_company":
                checks.append(
                    {
                        "name": "fab_no_entity_leak",
                        "ok": (detail.get("entity_leakage") or {}).get("score", 0) >= 100,
                        "detail": str((detail.get("entity_leakage") or {}).get("score")),
                    }
                )
    else:
        checkable = row.get("checkable") or 0
        checks.append(
            {
                "name": "fail_closed_no_checkable",
                "ok": checkable == 0,
                "detail": f"checkable={checkable}",
            }
        )
        by_ent = cov.get("by_entity") or {}
        invented = any((v.get("numeric") or 0) > 0 for v in by_ent.values())
        checks.append(
            {
                "name": "no_invented_numeric_claims",
                "ok": not invented,
                "detail": str(by_ent),
            }
        )
        checks.append(
            {
                "name": "recovery_completed_path",
                "ok": not crashed and status in {"incomplete_data", "needs_clarification"},
                "detail": f"status={status}",
            }
        )

    return {"ok": all(c["ok"] for c in checks), "checks": checks}
