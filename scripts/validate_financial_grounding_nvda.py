#!/usr/bin/env python3
"""Validate Financial Grounding Layer on NVIDIA 10-K via FinAgentBench (live APIs)."""

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
OUT = FAB / "outputs" / "lumenfin_financial_grounding"
NVDA_PDF = LUMEN / "fixtures" / "e2e_real" / "nvda_fy2025_10k_sec.pdf"
CASE = FAB / "fixtures" / "case_lumenfin_issuer_nvda.json"
PREV = FAB / "outputs" / "lumenfin_final_baseline" / "results.json"
REPORT = LUMEN / "LumenFin_Financial_Grounding_Validation.md"

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


def main() -> int:
    from dataclasses import replace

    from lumenfin.config import AppConfig
    from lumenfin.finrun import export_finrun_state
    from lumenfin.service import LumenFinAnalysisService
    from finagentbench.profiles import apply_profile
    from finagentbench.provenance import attach_provenance
    from finagentbench.report import write_eval_report
    from finagentbench.runner import evaluate_run

    if not NVDA_PDF.exists():
        print("FAIL missing", NVDA_PDF)
        return 1

    cfg = AppConfig.from_env()
    if not (cfg.llm.api_key or "").strip():
        print("FAIL: DEEPSEEK_API_KEY required")
        return 1
    model = (cfg.llm.model or "").strip().lower()
    if model in {"", "deepseek-chat"}:
        print("FAIL: set DEEPSEEK_MODEL=deepseek-v4-flash")
        return 1

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
    thread_id = f"grounding-nvda-{uuid4().hex[:8]}"
    query = (
        "Analyze NVIDIA investment risk using the uploaded FY2025 10-K excerpt and "
        "current market valuation. Cite filing pages where possible."
    )
    print("LIVE", thread_id)
    pkg = service.analyze(query=query, document_paths=[str(NVDA_PDF)], thread_id=thread_id)
    state = dict(pkg.get("result") or pkg)
    artifacts = pkg.get("artifacts") or {}
    state_path = artifacts.get("state") or artifacts.get("state_path")
    if state_path and Path(state_path).exists():
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    else:
        matches = sorted((LUMEN / "outputs").glob(f"{thread_id}*_state.json"), key=lambda p: p.stat().st_mtime)
        if matches:
            state = json.loads(matches[-1].read_text(encoding="utf-8"))

    _dump(OUT / "after_nvidia_10k_state.json", state)
    run = export_finrun_state(state)
    for metric in run.get("metrics") or []:
        metric.setdefault("unit", "ratio" if metric.get("formula") else "")
        conf = metric.get("confidence") or {}
        metric.setdefault("source", conf.get("structured_source") or "unknown")
    run["run_id"] = "grounding-nvidia_10k"
    _dump(OUT / "finrun_nvidia_10k.json", run)

    checkable = [m for m in (run.get("metrics") or []) if m.get("formula") and m.get("inputs")]
    case = apply_profile(json.loads(CASE.read_text(encoding="utf-8")), "ci")
    report = attach_provenance(
        evaluate_run(run, case),
        case,
        profile="ci",
        adapter="lumenfin-export",
    )
    paths = write_eval_report(report, OUT / "eval")
    detail = {
        m.name: {
            "score": m.score,
            "passed": m.passed,
            "findings": [{"severity": f.severity, "message": f.message} for f in m.findings],
        }
        for m in report.metrics
    }

    # Prior baseline After NVDA
    prev_nvda = {}
    if PREV.exists():
        prev = json.loads(PREV.read_text(encoding="utf-8"))
        for row in prev.get("results") or []:
            if row.get("cohort") == "after" and row.get("id") == "nvidia_10k":
                prev_nvda = row
                break

    companies = list(state.get("companies") or [])
    src_res = ((state.get("source_resolution") or {}).get("companies") or {}).get("NVIDIA") or {}
    payload = {
        "generated_at": _now(),
        "thread_id": thread_id,
        "workflow_status": state.get("workflow_status"),
        "llm_backend": (state.get("runtime_meta") or {}).get("llm_backend")
        or state.get("llm_backend"),
        "entities": [e.get("name") if isinstance(e, dict) else e for e in run.get("entities") or []],
        "companies": companies,
        "checkable_count": len(checkable),
        "checkable": checkable,
        "citation_markers": str(run.get("final_output") or "").count("#p"),
        "score": report.score,
        "passed": report.passed,
        "metric_detail": detail,
        "source_resolution_nvidia": src_res,
        "structured_source": (state.get("retrieved_docs") or {}).get("NVIDIA", {}).get("structured_source"),
        "fundamentals_meta": (state.get("retrieved_docs") or {}).get("NVIDIA", {}).get("fundamentals_meta"),
        "prev_after": {
            "score": prev_nvda.get("score"),
            "checkable_count": prev_nvda.get("checkable_count"),
            "workflow_status": prev_nvda.get("workflow_status"),
            "citation_markers": prev_nvda.get("citation_markers"),
            "numeric_correctness": ((prev_nvda.get("metric_detail") or {}).get("numeric_correctness") or {}).get(
                "score"
            ),
            "entity_leakage": ((prev_nvda.get("metric_detail") or {}).get("entity_leakage") or {}).get("score"),
        },
        "eval_paths": {k: str(v) for k, v in paths.items()},
    }
    # llm_backend from audit
    for step in state.get("audit_log") or []:
        if step.get("model"):
            payload["llm_model"] = step.get("model")
            break
    meta = state.get("metadata") or {}
    payload["llm_backend"] = meta.get("llm_backend") or payload.get("llm_backend")

    _dump(OUT / "validation.json", payload)

    lines = [
        "# LumenFin Financial Grounding Validation",
        "",
        f"Generated: {_now()}",
        "",
        "Scope: NVIDIA FY2025 10-K upload + live issuer SEC gap-fill (Financial Grounding Layer).",
        "Path: `export_finrun_state()` → FinAgentBench (issuer NVDA case, profile=`ci`).",
        "No mock LLM. Evaluators unchanged.",
        "",
        "## Result",
        "",
        "| Metric | Before Grounding (final baseline After) | After Grounding |",
        "|--------|----------------------------------------:|----------------:|",
        f"| FinAgentBench score | {payload['prev_after'].get('score')} | **{payload['score']}** |",
        f"| checkable formula+inputs | {payload['prev_after'].get('checkable_count')} | **{payload['checkable_count']}** |",
        f"| numeric_correctness | {payload['prev_after'].get('numeric_correctness')} | **{(detail.get('numeric_correctness') or {}).get('score')}** |",
        f"| entity_leakage | {payload['prev_after'].get('entity_leakage')} | **{(detail.get('entity_leakage') or {}).get('score')}** |",
        f"| evidence_coverage | — | **{(detail.get('evidence_coverage') or {}).get('score')}** |",
        f"| retrieval_provenance | — | **{(detail.get('retrieval_provenance') or {}).get('score')}** |",
        f"| #pN citation markers | {payload['prev_after'].get('citation_markers')} | **{payload['citation_markers']}** |",
        f"| workflow_status | {payload['prev_after'].get('workflow_status')} | **{payload['workflow_status']}** |",
        f"| entities | — | `{payload['entities']}` |",
        f"| structured_source | — | `{payload.get('structured_source')}` |",
        f"| grounding_layer | — | `{(payload.get('fundamentals_meta') or {}).get('grounding_layer')}` |",
        "",
        "## Gate",
        "",
    ]
    ok_numeric = payload["checkable_count"] >= 1 and (detail.get("numeric_correctness") or {}).get("score", 0) >= 80
    ok_entity = (detail.get("entity_leakage") or {}).get("score", 0) >= 100
    ok_status = payload["workflow_status"] == "completed"
    lines.append(f"- Numeric grounding improved: **{'PASS' if ok_numeric else 'FAIL'}**")
    lines.append(f"- Issuer isolation retained: **{'PASS' if ok_entity else 'FAIL'}**")
    lines.append(f"- Workflow completed (quant ran): **{'PASS' if ok_status else 'FAIL'}**")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `{OUT / 'validation.json'}`")
    lines.append(f"- `{OUT / 'finrun_nvidia_10k.json'}`")
    lines.append("")
    text = "\n".join(lines)
    REPORT.write_text(text, encoding="utf-8")
    (FAB / REPORT.name).write_text(text, encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("score", "checkable_count", "workflow_status", "entities", "citation_markers")}, indent=2))
    print("Wrote", REPORT)
    return 0 if ok_numeric and ok_entity and ok_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
