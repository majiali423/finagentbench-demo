#!/usr/bin/env python3
"""ARCHIVED AUDIT SCRIPT — unsupported release interface.

Historical purpose: production-hardening phase validation.
Replacement: scripts/run_rc_validation.py.
Last compatible schema: FinRun 1.0 transition.
Do not run against production fixtures.

Focus (no new claim rules):
  1) Long-document diligence
  2) Multi-company compare
  3) Multi-metric live/PDF grounding
  4) Fail-closed recovery (private company / sparse upload)

Path: live LumenFin → export_finrun_state() → FinAgentBench (ci).
Evaluators unchanged.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from repo_paths import finagentbench_root, lumenfin_root

LUMEN = lumenfin_root()
FAB = finagentbench_root()
OUT = FAB / "outputs" / "lumenfin_production_hardening"
FIX = LUMEN / "fixtures" / "e2e_real"
STRESS = LUMEN / "fixtures" / "stress"
REPORT = LUMEN / "LumenFin_Production_Hardening_Report.md"

sys.path.insert(0, str(FAB))
sys.path.insert(0, str(LUMEN / "src"))
os.chdir(LUMEN)

try:
    from dotenv import load_dotenv

    load_dotenv(LUMEN / ".env")
except Exception:
    pass


CASES: list[dict[str, Any]] = [
    {
        "id": "long_msft",
        "label": "Long document — Microsoft 10-K",
        "scenario": "long_document",
        "expect": "completed",
        "query": (
            "Using the uploaded Microsoft FY2024 long 10-K excerpt, analyze profitability, "
            "operating margin, R&D intensity, Intelligent Cloud signals, and key risk factors. "
            "Cite filing pages where possible."
        ),
        "docs": [FIX / "msft_fy2024_10k_sec_long.pdf"],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_nvda.json",  # replaced below with MSFT issuer
        "issuer": "Microsoft",
        "forbidden": ["Apple", "NVIDIA", "Amazon", "Alphabet", "Meta", "Tesla"],
    },
    {
        "id": "multi_compare",
        "label": "Multi-company — Apple vs Microsoft",
        "scenario": "multi_company",
        "expect": "completed",
        "query": (
            "Compare Apple and Microsoft FY2024 profitability, operating margin, and R&D intensity "
            "using live SEC/Yahoo fundamentals. Note platform or supply-chain risks briefly."
        ),
        "docs": [],
        "case": FAB / "fixtures" / "case_lumenfin_compare_aapl_msft.json",
        "expect_entities": ["Apple", "Microsoft"],
    },
    {
        "id": "multi_metric_long_aapl",
        "label": "Multi-metric long Apple 10-K",
        "scenario": "multi_metric",
        "expect": "completed",
        "query": (
            "From Apple's uploaded long FY2024 10-K, report revenue-linked profitability metrics "
            "(EBITDA/operating margin, R&D intensity), valuation context from live market data, "
            "and concentration/supply-chain risk conclusions with citations."
        ),
        "docs": [FIX / "aapl_fy2024_10k_sec_long.pdf"],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_aapl.json",
        "issuer": "Apple",
    },
    {
        "id": "fail_openai",
        "label": "Failure recovery — OpenAI fail-closed",
        "scenario": "failure_recovery",
        "expect": "incomplete_data",
        "query": (
            "Analyze OpenAI FY2025 annual profitability, operating margin, and R&D intensity "
            "using live fundamentals only. Do not invent estimates if data is unavailable."
        ),
        "docs": [],
        "case": None,  # internal checks only — gate failure expected
    },
    {
        "id": "fail_sparse",
        "label": "Failure recovery — sparse upload-only",
        "scenario": "failure_recovery",
        "expect": "incomplete_data",
        "query": (
            "Using only the uploaded Oracle fluff PDF, analyze FY profitability and operating margin. "
            "Do not use live SEC or Yahoo backfill."
        ),
        "docs": [STRESS / "oracle_sparse_fluff.pdf"],
        "case": None,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _ensure_msft_issuer_case() -> Path:
    path = FAB / "fixtures" / "case_lumenfin_issuer_msft.json"
    if path.exists():
        return path
    base = json.loads((FAB / "fixtures" / "case_lumenfin_issuer_aapl.json").read_text(encoding="utf-8"))
    base["id"] = "lumenfin_issuer_microsoft_001"
    base["query"] = "Issuer-only gate for Microsoft long 10-K diligence."
    base["expected_entities"] = ["Microsoft"]
    base["forbidden_entities"] = ["Apple", "NVIDIA", "Amazon", "Alphabet", "Meta", "Tesla", "Oracle"]
    # claim_binder is part of hardened graph
    steps = list(base.get("required_steps") or [])
    if "claim_binder" not in steps and "synthesizer" in steps:
        steps.insert(steps.index("synthesizer"), "claim_binder")
    base["required_steps"] = steps
    _dump(path, base)
    return path


def _patch_aapl_case_steps() -> None:
    for name in (
        "case_lumenfin_issuer_aapl.json",
        "case_lumenfin_issuer_nvda.json",
        "case_lumenfin_issuer_tsla.json",
    ):
        path = FAB / "fixtures" / name
        if not path.exists():
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        steps = list(case.get("required_steps") or [])
        if "claim_binder" not in steps and "synthesizer" in steps:
            steps.insert(steps.index("synthesizer"), "claim_binder")
            case["required_steps"] = steps
            _dump(path, case)


def _live_analyze(query: str, docs: list[Path], prefix: str) -> tuple[dict[str, Any], float, str | None]:
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
        milvus_uri=str(OUT / f"milvus_{uuid4().hex[:8]}.db"),
        milvus_isolate=True,
        output_dir=OUT / "states",
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
                (LUMEN / "outputs").glob(f"{thread_id}*_state.json"),
                key=lambda p: p.stat().st_mtime,
            )
            alt = sorted((OUT / "states").glob(f"{thread_id}*_state.json"), key=lambda p: p.stat().st_mtime)
            matches = matches or alt
            if matches:
                state = json.loads(matches[-1].read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        state = {"workflow_status": "crashed", "error": err, "traceback": traceback.format_exc()[-2000:]}
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    state.setdefault("thread_id", thread_id)
    return state, elapsed_ms, err


def _export(state: dict[str, Any]) -> dict[str, Any]:
    from lumenfin.finrun import export_finrun_state

    run = export_finrun_state(state)
    for metric in run.get("metrics") or []:
        metric.setdefault("unit", "ratio" if metric.get("formula") else "")
        conf = metric.get("confidence") or {}
        metric.setdefault("source", conf.get("structured_source") or "unknown")
    return run


def _evaluate(run: dict[str, Any], case_path: Path, out_dir: Path) -> dict[str, Any]:
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
    detail = {
        m.name: {"score": m.score, "passed": m.passed}
        for m in report.metrics
    }
    return {"score": report.score, "passed": report.passed, "metric_detail": detail}


def _claim_coverage(state: dict[str, Any], final_output: str) -> dict[str, Any]:
    from lumenfin.claims import claims_from_state, filter_verified

    claims = claims_from_state(state)
    verified = filter_verified(claims)
    binding = state.get("claim_binding") or {}
    by_entity: dict[str, dict[str, int]] = {}
    for claim in verified:
        bucket = by_entity.setdefault(claim.entity, {"verified": 0, "numeric": 0, "risk": 0, "investment": 0})
        bucket["verified"] += 1
        if claim.claim_type == "numeric":
            bucket["numeric"] += 1
        elif claim.claim_type == "risk_conclusion":
            bucket["risk"] += 1
        elif claim.claim_type == "investment_conclusion":
            bucket["investment"] += 1
    in_report = sum(1 for c in verified if c.primary_citation and c.primary_citation in final_output)
    companies = list(state.get("companies") or [])
    entities_with_numeric = sum(1 for e in companies if (by_entity.get(e) or {}).get("numeric", 0) > 0)
    return {
        "binding": binding,
        "verified_total": len(verified),
        "verified_in_report": in_report,
        "report_coverage": round(in_report / len(verified), 4) if verified else 0.0,
        "by_entity": by_entity,
        "entities_with_numeric_claims": entities_with_numeric,
        "entity_claim_coverage": round(entities_with_numeric / len(companies), 4) if companies else 0.0,
        "page_anchored": binding.get("page_anchored_verified", 0),
        "citation_markers": final_output.count("#p"),
    }


def _judge(row: dict[str, Any]) -> dict[str, Any]:
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
                "ok": (cov.get("verified_total") or 0) >= 3 and (cov.get("report_coverage") or 0) >= 0.8,
                "detail": f"verified={cov.get('verified_total')} report_cov={cov.get('report_coverage')}",
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
                    "ok": row.get("workflow_status") == "completed" and (row.get("checkable") or 0) >= 1,
                    "detail": f"checkable={row.get('checkable')} markers={cov.get('citation_markers')}",
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
        # failure recovery
        checkable = row.get("checkable") or 0
        checks.append(
            {
                "name": "fail_closed_no_checkable",
                "ok": checkable == 0,
                "detail": f"checkable={checkable}",
            }
        )
        # Should not invent AST ratios as verified numeric facts from sample
        by_ent = (cov.get("by_entity") or {})
        invented = any((v.get("numeric") or 0) > 0 for v in by_ent.values())
        # OpenAI/sparse may still have zero numeric verified — good
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

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}


def main() -> int:
    _patch_aapl_case_steps()
    msft_case = _ensure_msft_issuer_case()
    for spec in CASES:
        if spec["id"] == "long_msft":
            spec["case"] = msft_case

    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for spec in CASES:
        docs = [Path(d) for d in (spec.get("docs") or [])]
        missing = [str(d) for d in docs if not d.exists()]
        if missing:
            rows.append(
                {
                    "id": spec["id"],
                    "label": spec["label"],
                    "scenario": spec["scenario"],
                    "expect": spec["expect"],
                    "error": f"missing fixtures: {missing}",
                    "workflow_status": "crashed",
                    "judgment": {"ok": False, "checks": [{"name": "fixtures", "ok": False, "detail": str(missing)}]},
                }
            )
            continue

        state, elapsed_ms, err = _live_analyze(spec["query"], docs, f"harden-{spec['id']}")
        _dump(OUT / "states" / f"{spec['id']}_state.json", state)
        run = _export(state) if state.get("workflow_status") != "crashed" else {"metrics": [], "entities": [], "final_output": ""}
        if state.get("workflow_status") != "crashed":
            run["run_id"] = f"harden-{spec['id']}"
            _dump(OUT / "finrun" / f"{spec['id']}.json", run)

        final_output = str(run.get("final_output") or state.get("final_report") or "")
        cov = _claim_coverage(state, final_output) if state.get("workflow_status") != "crashed" else {}
        fab = None
        if spec.get("case") and state.get("workflow_status") == "completed":
            try:
                fab = _evaluate(run, Path(spec["case"]), OUT / "eval" / spec["id"])
            except Exception as exc:  # noqa: BLE001
                fab = {"error": str(exc)}

        row = {
            "id": spec["id"],
            "label": spec["label"],
            "scenario": spec["scenario"],
            "expect": spec["expect"],
            "expect_entities": spec.get("expect_entities"),
            "workflow_status": state.get("workflow_status"),
            "error": err,
            "elapsed_ms": round(elapsed_ms, 1),
            "entities": [e.get("name") if isinstance(e, dict) else e for e in run.get("entities") or []]
            or list(state.get("companies") or []),
            "checkable": len([m for m in (run.get("metrics") or []) if m.get("formula") and m.get("inputs")]),
            "llm_backend": (state.get("metadata") or {}).get("llm_backend") or state.get("llm_backend"),
            "claim_coverage": cov,
            "fab": fab,
            "steps": [s.get("name") for s in (run.get("steps") or [])],
        }
        # llm backend from audit
        for step in state.get("audit_log") or []:
            if step.get("model"):
                row["llm_model"] = step.get("model")
                break
        meta = state.get("metadata") or {}
        row["llm_backend"] = meta.get("llm_backend") or row.get("llm_backend")

        row["judgment"] = _judge(row)
        rows.append(row)
        print(
            f"[{spec['id']}] status={row['workflow_status']} ok={row['judgment']['ok']} "
            f"verified={cov.get('verified_total')} report_cov={cov.get('report_coverage')} "
            f"fab={((fab or {}).get('score'))} elapsed_ms={row['elapsed_ms']}",
            flush=True,
        )

    payload = {"generated_at": _now(), "rows": rows}
    _dump(OUT / "validation.json", payload)
    _write_report(rows)
    print("Wrote", REPORT)
    return 0 if all((r.get("judgment") or {}).get("ok") for r in rows) else 2


def _write_report(rows: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# LumenFin Production Hardening Report")
    lines.append("")
    lines.append(f"Generated: {_now()}")
    lines.append("")
    lines.append(
        "Scope: **claim coverage**, **failure recovery**, and **reliability** under long-document, "
        "multi-company, and multi-metric stress — **without adding new claim rules**."
    )
    lines.append("")
    lines.append("Path: live LumenFin → `export_finrun_state()` → FinAgentBench (`ci`). Evaluators unchanged.")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    passed = sum(1 for r in rows if (r.get("judgment") or {}).get("ok"))
    lines.append(f"| Cases | Passed |")
    lines.append(f"|------:|-------:|")
    lines.append(f"| {len(rows)} | **{passed}/{len(rows)}** |")
    lines.append("")
    lines.append("| Case | Scenario | Status | OK | Verified claims | Report coverage | #pN | Checkable | FAB score | Elapsed ms |")
    lines.append("|------|----------|--------|:--:|----------------:|----------------:|----:|----------:|----------:|-----------:|")
    for r in rows:
        cov = r.get("claim_coverage") or {}
        fab = r.get("fab") or {}
        lines.append(
            f"| {r.get('label')} | {r.get('scenario')} | `{r.get('workflow_status')}` | "
            f"{'Y' if (r.get('judgment') or {}).get('ok') else 'N'} | "
            f"{cov.get('verified_total')} | {cov.get('report_coverage')} | "
            f"{cov.get('citation_markers')} | {r.get('checkable')} | {fab.get('score')} | {r.get('elapsed_ms')} |"
        )
    lines.append("")
    lines.append("## 2. Claim Coverage")
    lines.append("")
    lines.append("| Case | Bind rate | Entities w/ numeric claims | Entity claim coverage | Page-anchored verified | Verified citations in report |")
    lines.append("|------|----------:|---------------------------:|----------------------:|-----------------------:|-----------------------------:|")
    for r in rows:
        if r.get("expect") != "completed":
            continue
        cov = r.get("claim_coverage") or {}
        binding = cov.get("binding") or {}
        lines.append(
            f"| {r.get('label')} | {binding.get('bind_rate')} | {cov.get('entities_with_numeric_claims')} | "
            f"{cov.get('entity_claim_coverage')} | {cov.get('page_anchored')} | "
            f"{cov.get('verified_in_report')}/{cov.get('verified_total')} |"
        )
    lines.append("")
    multi = next((r for r in rows if r.get("id") == "multi_compare"), None)
    if multi:
        lines.append("### Multi-company per-entity claims")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps((multi.get("claim_coverage") or {}).get("by_entity") or {}, indent=2))
        lines.append("```")
        lines.append("")
    lines.append("## 3. Failure Recovery")
    lines.append("")
    lines.append("| Case | Expected | Got | No crash | No invented numeric claims | Checkable=0 |")
    lines.append("|------|----------|-----|:--------:|:--------------------------:|:-----------:|")
    for r in rows:
        if r.get("scenario") != "failure_recovery":
            continue
        checks = {(c["name"]): c for c in ((r.get("judgment") or {}).get("checks") or [])}
        lines.append(
            f"| {r.get('label')} | `{r.get('expect')}` | `{r.get('workflow_status')}` | "
            f"{'Y' if (checks.get('no_crash') or {}).get('ok') else 'N'} | "
            f"{'Y' if (checks.get('no_invented_numeric_claims') or {}).get('ok') else 'N'} | "
            f"{'Y' if (checks.get('fail_closed_no_checkable') or {}).get('ok') else 'N'} |"
        )
    lines.append("")
    lines.append("## 4. Reliability (FinAgentBench — completed cases)")
    lines.append("")
    lines.append("| Case | Score | evidence_coverage | evidence_consistency | numeric_correctness | entity_leakage |")
    lines.append("|------|------:|------------------:|---------------------:|--------------------:|---------------:|")
    for r in rows:
        fab = r.get("fab") or {}
        if not fab or fab.get("error"):
            continue
        d = fab.get("metric_detail") or {}
        def sc(name: str) -> Any:
            return (d.get(name) or {}).get("score")
        lines.append(
            f"| {r.get('label')} | {fab.get('score')} | {sc('evidence_coverage')} | "
            f"{sc('evidence_consistency')} | {sc('numeric_correctness')} | {sc('entity_leakage')} |"
        )
    lines.append("")
    lines.append("## 5. Gate Details")
    lines.append("")
    for r in rows:
        lines.append(f"### {r.get('label')}")
        lines.append("")
        for c in ((r.get("judgment") or {}).get("checks") or []):
            mark = "PASS" if c.get("ok") else "FAIL"
            lines.append(f"- **{mark}** `{c.get('name')}` — {c.get('detail')}")
        lines.append("")
    lines.append("## 6. Verdict")
    lines.append("")
    all_ok = all((r.get("judgment") or {}).get("ok") for r in rows)
    lines.append(
        "**PASS — production hardening suite green.**"
        if all_ok
        else "**PARTIAL/FAIL — see gate details; prioritize failure-type fixes, not new claim rules.**"
    )
    lines.append("")
    lines.append("Hardening focus remains: long-doc claim coverage, multi-entity claim parity, and fail-closed recovery under live APIs.")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `{OUT / 'validation.json'}`")
    lines.append(f"- FinRuns: `{OUT / 'finrun'}`")
    lines.append("")
    text = "\n".join(lines)
    REPORT.write_text(text, encoding="utf-8")
    (FAB / REPORT.name).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
