#!/usr/bin/env python3
"""ARCHIVED AUDIT SCRIPT — unsupported release interface.

Historical purpose: Before/After claim-to-evidence binding validation.
Replacement: current claim-binding tests and scripts/run_rc_validation.py.
Last compatible schema: FinRun 1.0 transition.
Do not run against production fixtures.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from repo_paths import finagentbench_root, lumenfin_root

FAB = finagentbench_root()
LUMEN = lumenfin_root()
OUT = FAB / "outputs" / "lumenfin_claim_binding"
NVDA_PDF = LUMEN / "fixtures" / "e2e_real" / "nvda_fy2025_10k_sec.pdf"
CASE_NVDA = FAB / "fixtures" / "case_lumenfin_issuer_nvda.json"
CASE_AAPL = FAB / "fixtures" / "case_lumenfin_issuer_aapl.json"
PREV_BASELINE = FAB / "outputs" / "lumenfin_final_baseline" / "results.json"
PREV_GROUNDING = FAB / "outputs" / "lumenfin_financial_grounding" / "validation.json"
REPORT = LUMEN / "LumenFin_Claim_Evidence_Binding_Report.md"

sys.path.insert(0, str(FAB))
sys.path.insert(0, str(LUMEN / "src"))
os.chdir(LUMEN)

try:
    from dotenv import load_dotenv

    load_dotenv(LUMEN / ".env")
except Exception:
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _evaluate(run: dict, case_path: Path, out_dir: Path) -> dict:
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
        m.name: {
            "score": m.score,
            "passed": m.passed,
            "findings": [{"severity": f.severity, "message": f.message} for f in m.findings],
        }
        for m in report.metrics
    }
    return {"score": report.score, "passed": report.passed, "metric_detail": detail}


def _live(query: str, docs: list[str], prefix: str) -> dict:
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
    )
    service = LumenFinAnalysisService(cfg)
    thread_id = f"{prefix}-{uuid4().hex[:8]}"
    print("LIVE", thread_id, docs[:1] if docs else None)
    pkg = service.analyze(query=query, document_paths=docs or None, thread_id=thread_id)
    state = dict(pkg.get("result") or pkg)
    artifacts = pkg.get("artifacts") or {}
    sp = artifacts.get("state") or artifacts.get("state_path")
    if sp and Path(sp).exists():
        state = json.loads(Path(sp).read_text(encoding="utf-8"))
    else:
        matches = sorted((LUMEN / "outputs").glob(f"{thread_id}*_state.json"), key=lambda p: p.stat().st_mtime)
        if matches:
            state = json.loads(matches[-1].read_text(encoding="utf-8"))
    return state


def _export(state: dict) -> dict:
    from lumenfin.finrun import export_finrun_state

    run = export_finrun_state(state)
    for metric in run.get("metrics") or []:
        metric.setdefault("unit", "ratio" if metric.get("formula") else "")
        conf = metric.get("confidence") or {}
        metric.setdefault("source", conf.get("structured_source") or "unknown")
    return run


def _metrics_row(detail: dict) -> dict:
    keys = (
        "evidence_coverage",
        "evidence_consistency",
        "retrieval_provenance",
        "numeric_correctness",
        "entity_leakage",
        "risk_disclosure",
    )
    return {k: (detail.get(k) or {}).get("score") for k in keys}


def main() -> int:
    from lumenfin.claims import claims_from_state, filter_verified

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    # --- NVIDIA PDF (citation-heavy) ---
    nvda_state = _live(
        "Analyze NVIDIA investment risk using the uploaded FY2025 10-K excerpt and "
        "current market valuation. Cite filing pages where possible.",
        [str(NVDA_PDF)],
        "claimbind-nvda",
    )
    _dump(OUT / "after_nvidia_state.json", nvda_state)
    nvda_run = _export(nvda_state)
    nvda_run["run_id"] = "claimbind-nvidia"
    _dump(OUT / "finrun_nvidia.json", nvda_run)
    nvda_ev = _evaluate(nvda_run, CASE_NVDA, OUT / "eval" / "nvidia")
    nvda_verified = filter_verified(claims_from_state(nvda_state))
    inline_cited = sum(1 for c in nvda_verified if c.primary_citation and c.primary_citation in str(nvda_run.get("final_output") or ""))
    rows.append(
        {
            "id": "nvidia_10k",
            "label": "NVIDIA 10-K",
            "workflow_status": nvda_state.get("workflow_status"),
            "entities": [e.get("name") if isinstance(e, dict) else e for e in nvda_run.get("entities") or []],
            "checkable": len([m for m in (nvda_run.get("metrics") or []) if m.get("formula") and m.get("inputs")]),
            "citation_markers": str(nvda_run.get("final_output") or "").count("#p"),
            "claim_binding": nvda_state.get("claim_binding") or {},
            "verified_in_report": inline_cited,
            "verified_total": len(nvda_verified),
            **nvda_ev,
            "focus": _metrics_row(nvda_ev["metric_detail"]),
        }
    )

    # --- Apple live (fundamentals citations, may have 0 #pN) ---
    apple_state = _live(
        "Analyze Apple FY2024 annual profitability, operating margin, and R&D intensity "
        "using live fundamentals. Discuss valuation context with current market snapshot.",
        [],
        "claimbind-apple",
    )
    _dump(OUT / "after_apple_state.json", apple_state)
    apple_run = _export(apple_state)
    apple_run["run_id"] = "claimbind-apple"
    _dump(OUT / "finrun_apple.json", apple_run)
    apple_ev = _evaluate(apple_run, CASE_AAPL, OUT / "eval" / "apple")
    apple_verified = filter_verified(claims_from_state(apple_state))
    apple_inline = sum(
        1
        for c in apple_verified
        if c.primary_citation and c.primary_citation in str(apple_run.get("final_output") or "")
    )
    rows.append(
        {
            "id": "apple_live",
            "label": "Apple live",
            "workflow_status": apple_state.get("workflow_status"),
            "entities": [e.get("name") if isinstance(e, dict) else e for e in apple_run.get("entities") or []],
            "checkable": len([m for m in (apple_run.get("metrics") or []) if m.get("formula") and m.get("inputs")]),
            "citation_markers": str(apple_run.get("final_output") or "").count("#p"),
            "claim_binding": apple_state.get("claim_binding") or {},
            "verified_in_report": apple_inline,
            "verified_total": len(apple_verified),
            **apple_ev,
            "focus": _metrics_row(apple_ev["metric_detail"]),
        }
    )

    # Before snapshots
    before_nvda = {}
    before_apple = {}
    if PREV_BASELINE.exists():
        prev = json.loads(PREV_BASELINE.read_text(encoding="utf-8"))
        for row in prev.get("results") or []:
            if row.get("cohort") != "after":
                continue
            if row.get("id") == "nvidia_10k":
                before_nvda = row
            if row.get("id") == "apple_live":
                before_apple = row
    if PREV_GROUNDING.exists():
        g = json.loads(PREV_GROUNDING.read_text(encoding="utf-8"))
        # Prefer grounding as more recent NVDA before for numeric baseline
        before_nvda_grounded = {
            "score": g.get("score"),
            "checkable_count": g.get("checkable_count"),
            "citation_markers": g.get("citation_markers"),
            "workflow_status": g.get("workflow_status"),
            "metric_detail": {
                "numeric_correctness": {"score": ((g.get("metric_detail") or {}).get("numeric_correctness") or {}).get("score")},
                "evidence_coverage": {"score": ((g.get("metric_detail") or {}).get("evidence_coverage") or {}).get("score")},
                "entity_leakage": {"score": ((g.get("metric_detail") or {}).get("entity_leakage") or {}).get("score")},
            },
        }
        if before_nvda_grounded.get("score") is not None:
            before_nvda = {**before_nvda, **before_nvda_grounded, "id": "nvidia_10k", "label": "NVIDIA 10-K (post-grounding)"}

    payload = {"generated_at": _now(), "rows": rows, "before_nvda": before_nvda, "before_apple": before_apple}
    _dump(OUT / "validation.json", payload)

    def sc(row: dict, metric: str):
        return ((row.get("metric_detail") or {}).get(metric) or {}).get("score")

    nvda = rows[0]
    apple = rows[1]
    lines = [
        "# LumenFin Claim → Evidence Binding Report",
        "",
        f"Generated: {_now()}",
        "",
        "Path: `claim_binder` → synthesizer (verified claims only) → `export_finrun_state()` → FinAgentBench (`ci`).",
        "Evaluators unchanged. Citations are structural (no prompt-forced citation generation).",
        "",
        "## 1. Current Score",
        "",
        "| Case | Before score | After score | Before #pN | After #pN | Verified claims | Verified citations in report |",
        "|------|-------------:|------------:|-----------:|----------:|----------------:|-----------------------------:|",
        f"| NVIDIA 10-K | {before_nvda.get('score')} | **{nvda['score']}** | {before_nvda.get('citation_markers')} | **{nvda['citation_markers']}** | {nvda['verified_total']} | {nvda['verified_in_report']} |",
        f"| Apple live | {before_apple.get('score')} | **{apple['score']}** | {before_apple.get('citation_markers')} | **{apple['citation_markers']}** | {apple['verified_total']} | {apple['verified_in_report']} |",
        "",
        "## 2. Citation / Evidence Metrics (After)",
        "",
        "| Case | evidence_coverage | evidence_consistency | retrieval_provenance | numeric_correctness | entity_leakage |",
        "|------|------------------:|---------------------:|---------------------:|--------------------:|---------------:|",
        f"| NVIDIA | {nvda['focus'].get('evidence_coverage')} | {nvda['focus'].get('evidence_consistency')} | {nvda['focus'].get('retrieval_provenance')} | {nvda['focus'].get('numeric_correctness')} | {nvda['focus'].get('entity_leakage')} |",
        f"| Apple | {apple['focus'].get('evidence_coverage')} | {apple['focus'].get('evidence_consistency')} | {apple['focus'].get('retrieval_provenance')} | {apple['focus'].get('numeric_correctness')} | {apple['focus'].get('entity_leakage')} |",
        "",
        "## 3. Before / After Comparison",
        "",
        "| Dimension | Before | After | Read |",
        "|-----------|--------|-------|------|",
        f"| NVIDIA claim→citation in body | appendix #pN only / unbound metrics | verified claims rendered with [citation] inline | Structural binding |",
        f"| NVIDIA bind_rate | ~0 (no claim objects) | {(nvda.get('claim_binding') or {}).get('bind_rate')} | Internal claim filter |",
        f"| Apple live citations | 0 `#pN` (no upload) | {apple['citation_markers']} `#pN`; fundamentals citations on verified claims | Expected for live-only |",
        f"| Growth claims | heuristic possible | rejected without multi-period fundamentals | Fail-closed |",
        f"| Investment conclusions | template prose | verified composition from numeric+risk only | Fail-closed |",
        "",
        "## 4. Claim Binding Detail",
        "",
        f"- NVIDIA: `{json.dumps(nvda.get('claim_binding') or {}, ensure_ascii=False)}`",
        f"- Apple: `{json.dumps(apple.get('claim_binding') or {}, ensure_ascii=False)}`",
        "",
        "## 5. Gate",
        "",
    ]
    ok_nvda = (
        nvda["verified_total"] >= 3
        and nvda["verified_in_report"] >= 3
        and (nvda["focus"].get("evidence_coverage") or 0) >= 100
        and (nvda["focus"].get("numeric_correctness") or 0) >= 80
        and nvda["workflow_status"] == "completed"
    )
    ok_apple = (
        apple["verified_total"] >= 3
        and apple["verified_in_report"] >= 3
        and (apple["focus"].get("evidence_coverage") or 0) >= 100
        and apple["workflow_status"] == "completed"
    )
    lines.append(f"- NVIDIA verified claim binding: **{'PASS' if ok_nvda else 'FAIL'}**")
    lines.append(f"- Apple verified claim binding: **{'PASS' if ok_apple else 'FAIL'}**")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `{OUT / 'validation.json'}`")
    lines.append("")

    text = "\n".join(lines)
    REPORT.write_text(text, encoding="utf-8")
    (FAB / REPORT.name).write_text(text, encoding="utf-8")
    print(json.dumps({"nvidia": {k: nvda[k] for k in ('score','citation_markers','verified_total','verified_in_report','workflow_status')}, "apple": {k: apple[k] for k in ('score','citation_markers','verified_total','verified_in_report','workflow_status')}}, indent=2))
    print("Wrote", REPORT)
    return 0 if ok_nvda and ok_apple else 2


if __name__ == "__main__":
    raise SystemExit(main())
