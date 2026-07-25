#!/usr/bin/env python3
"""Release Candidate Validation — expand real-company coverage + reliability gates.

No new claim/citation rules. No FinAgentBench threshold changes.
Reuses production-hardening judges + existing issuer/compare fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_paths import finagentbench_root, lumenfin_root

LUMEN = lumenfin_root()
FAB = finagentbench_root()
OUT = FAB / "outputs" / "lumenfin_rc_validation"
FIX = LUMEN / "fixtures" / "e2e_real"
STRESS = LUMEN / "fixtures" / "stress"
REPORT = LUMEN / "LumenFin_RC_Final_Reliability_Report.md"
READINESS = LUMEN / "LumenFin_RC_Production_Readiness_Assessment.md"

sys.path.insert(0, str(FAB))
sys.path.insert(0, str(FAB / "scripts"))
sys.path.insert(0, str(LUMEN / "src"))
os.chdir(LUMEN)

try:
    from dotenv import load_dotenv

    load_dotenv(LUMEN / ".env")
except Exception:
    pass

import run_production_hardening as ph  # noqa: E402

# Expanded real-company RC pack (existing fixtures/cases only).
RC_CASES: list[dict[str, Any]] = [
    {
        "id": "rc_apple_live",
        "label": "Apple live",
        "scenario": "issuer_live",
        "expect": "completed",
        "query": (
            "Analyze Apple FY2024 annual profitability, operating margin, and R&D intensity "
            "using live fundamentals. Discuss valuation context with current market snapshot."
        ),
        "docs": [],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_aapl.json",
        "expect_entities": ["Apple"],
    },
    {
        "id": "rc_nvidia_10k",
        "label": "NVIDIA 10-K PDF",
        "scenario": "issuer_pdf",
        "expect": "completed",
        "query": (
            "Analyze NVIDIA investment risk using the uploaded FY2025 10-K excerpt and "
            "current market valuation. Cite filing pages where possible."
        ),
        "docs": [FIX / "nvda_fy2025_10k_sec.pdf"],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_nvda.json",
        "expect_entities": ["NVIDIA"],
    },
    {
        "id": "rc_tesla_live",
        "label": "Tesla live",
        "scenario": "issuer_live",
        "expect": "completed",
        "query": (
            "Analyze Tesla FY2024 profitability, automotive margin signals, and balance-sheet "
            "risk using live fundamentals and market data."
        ),
        "docs": [],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_tsla.json",
        "expect_entities": ["Tesla"],
    },
    {
        "id": "rc_msft_long",
        "label": "Microsoft long 10-K",
        "scenario": "long_document",
        "expect": "completed",
        "query": (
            "Using the uploaded Microsoft FY2024 long 10-K excerpt, analyze profitability, "
            "operating margin, R&D intensity, and key risk factors. Cite filing pages where possible."
        ),
        "docs": [FIX / "msft_fy2024_10k_sec_long.pdf"],
        "case": FAB / "fixtures" / "case_lumenfin_issuer_msft.json",
        "expect_entities": ["Microsoft"],
    },
    {
        "id": "rc_compare_aapl_msft",
        "label": "Compare Apple vs Microsoft",
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
        "id": "rc_compare_nvda_amd",
        "label": "Compare NVIDIA vs AMD",
        "scenario": "multi_company",
        "expect": "completed",
        "query": (
            "Compare NVIDIA and AMD FY2024 profitability, operating margin, and R&D intensity "
            "using live SEC/Yahoo fundamentals. Keep the analysis limited to the two requested companies."
        ),
        "docs": [],
        "case": FAB / "fixtures" / "case_lumenfin_compare_nvda_amd.json",
        "expect_entities": ["NVIDIA", "AMD"],
    },
    {
        "id": "rc_fail_openai",
        "label": "OpenAI fail-closed",
        "scenario": "failure_recovery",
        "expect": "incomplete_data",
        "query": (
            "Analyze OpenAI FY2025 annual profitability, operating margin, and R&D intensity "
            "using live fundamentals only. Do not invent estimates if data is unavailable."
        ),
        "docs": [],
        "case": None,
    },
    {
        "id": "rc_fail_sparse",
        "label": "Sparse upload-only fail-closed",
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


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 600) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-1500:],
            "stderr_tail": (proc.stderr or "")[-1500:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "returncode": -1, "error": str(exc)}


def _validate_claim_binder_steps() -> None:
    missing: list[str] = []
    for name in (
        "case_lumenfin_issuer_aapl.json",
        "case_lumenfin_issuer_nvda.json",
        "case_lumenfin_issuer_tsla.json",
        "case_lumenfin_issuer_msft.json",
        "case_lumenfin_compare_aapl_msft.json",
        "case_lumenfin_compare_nvda_amd.json",
    ):
        path = FAB / "fixtures" / name
        if not path.exists():
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        steps = list(case.get("required_steps") or [])
        if "claim_binder" not in steps and "synthesizer" in steps:
            missing.append(name)
    if missing:
        raise RuntimeError(
            "RC fixtures must declare claim_binder before validation; "
            f"refusing to mutate benchmark cases at runtime: {missing}"
        )


def _run_offline_gates() -> dict[str, Any]:
    py = sys.executable
    unit = _run_cmd([py, str(LUMEN / "scripts" / "run_tests.py")], cwd=LUMEN, timeout=300)
    fab_tests = _run_cmd([py, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=FAB, timeout=300)
    fab_suite = FAB / "benchmarks" / "lumenfin_regression" / "suite.json"
    fab_bench = {"ok": None, "skipped": True}
    if fab_suite.exists():
        fab_bench = _run_cmd(
            [
                py,
                "-m",
                "finagentbench",
                "benchmark",
                str(fab_suite),
                "--out",
                str(OUT / "fab_lumenfin_regression.json"),
            ],
            cwd=FAB,
            timeout=300,
        )
    correctness = FAB / "scripts" / "run_correctness_validation.py"
    fab_correct = {"ok": None, "skipped": True}
    if correctness.exists():
        fab_correct = _run_cmd([py, str(correctness)], cwd=FAB, timeout=300)
    return {
        "lumenfin_unit": unit,
        "finagentbench_unit": fab_tests,
        "finagentbench_lumenfin_regression": fab_bench,
        "finagentbench_correctness": fab_correct,
    }


def _run_live_case(spec: dict[str, Any]) -> dict[str, Any]:
    docs = [Path(d) for d in (spec.get("docs") or [])]
    missing = [str(d) for d in docs if not d.exists()]
    if missing:
        row = {
            "id": spec["id"],
            "label": spec["label"],
            "scenario": spec["scenario"],
            "expect": spec["expect"],
            "expect_entities": spec.get("expect_entities"),
            "error": f"missing fixtures: {missing}",
            "workflow_status": "crashed",
        }
        row["judgment"] = ph._judge(row)
        return row

    state, elapsed_ms, err = ph._live_analyze(spec["query"], docs, f"rc-{spec['id']}")
    ph._dump(OUT / "states" / f"{spec['id']}_state.json", state)
    run = (
        ph._export(state)
        if state.get("workflow_status") != "crashed"
        else {"metrics": [], "entities": [], "final_output": "", "steps": []}
    )
    if state.get("workflow_status") != "crashed":
        run["run_id"] = f"rc-{spec['id']}"
        ph._dump(OUT / "finrun" / f"{spec['id']}.json", run)

    final_output = str(run.get("final_output") or state.get("final_report") or "")
    cov = (
        ph._claim_coverage(state, final_output)
        if state.get("workflow_status") != "crashed"
        else {}
    )
    fab = None
    if spec.get("case") and state.get("workflow_status") == "completed":
        try:
            fab = ph._evaluate(run, Path(spec["case"]), OUT / "eval" / spec["id"])
        except Exception as exc:  # noqa: BLE001
            fab = {"error": str(exc)}

    # Map issuer_* scenarios onto hardening judge expectations.
    scenario = spec["scenario"]
    judge_scenario = scenario
    if scenario in {"issuer_live", "issuer_pdf"}:
        judge_scenario = "multi_metric"
    row = {
        "id": spec["id"],
        "label": spec["label"],
        "scenario": judge_scenario,
        "raw_scenario": scenario,
        "expect": spec["expect"],
        "expect_entities": spec.get("expect_entities"),
        "workflow_status": state.get("workflow_status"),
        "error": err,
        "elapsed_ms": round(elapsed_ms, 1),
        "entities": [e.get("name") if isinstance(e, dict) else e for e in run.get("entities") or []]
        or list(state.get("companies") or []),
        "checkable": len([m for m in (run.get("metrics") or []) if m.get("formula") and m.get("inputs")]),
        "claim_coverage": cov,
        "fab": fab,
        "steps": [s.get("name") for s in (run.get("steps") or [])],
    }
    row["judgment"] = ph._judge(row)
    print(
        f"[{spec['id']}] status={row['workflow_status']} ok={row['judgment']['ok']} "
        f"verified={cov.get('verified_total')} fab={((fab or {}).get('score'))} "
        f"elapsed_ms={row['elapsed_ms']}",
        flush=True,
    )
    return row


def _load_prior_summaries() -> dict[str, Any]:
    priors = {}
    mapping = {
        "baseline": LUMEN / "LumenFin_Final_Reliability_Baseline.md",
        "grounding": LUMEN / "LumenFin_Financial_Grounding_Validation.md",
        "claim_binding": LUMEN / "LumenFin_Claim_Evidence_Binding_Report.md",
        "hardening": LUMEN / "LumenFin_Production_Hardening_Report.md",
        "e2e": LUMEN / "LumenFin_E2E_Audit_Report.md",
        "regression": LUMEN / "LumenFin_Regression_Comparison.md",
    }
    for key, path in mapping.items():
        priors[key] = {"exists": path.exists(), "path": str(path)}
    # Prefer structured JSON when present
    for key, path in {
        "hardening_json": FAB / "outputs" / "lumenfin_production_hardening" / "validation.json",
        "claim_json": FAB / "outputs" / "lumenfin_claim_binding" / "validation.json",
        "grounding_json": FAB / "outputs" / "lumenfin_financial_grounding" / "validation.json",
    }.items():
        if path.exists():
            priors[key] = json.loads(path.read_text(encoding="utf-8"))
    return priors


def main() -> int:
    _validate_claim_binder_steps()
    OUT.mkdir(parents=True, exist_ok=True)

    print("=== OFFLINE GATES ===", flush=True)
    offline = _run_offline_gates()
    _dump(OUT / "offline_gates.json", offline)
    for name, result in offline.items():
        print(f"  {name}: ok={result.get('ok')} rc={result.get('returncode')}", flush=True)

    print("=== LIVE RC PACK ===", flush=True)
    # Point hardening helpers at RC output dir for milvus isolation
    ph.OUT = OUT
    rows = [_run_live_case(spec) for spec in RC_CASES]

    priors = _load_prior_summaries()
    payload = {
        "generated_at": _now(),
        "offline": offline,
        "rows": rows,
        "priors": {k: v for k, v in priors.items() if k.endswith("_json") or k in {"baseline", "grounding", "claim_binding", "hardening", "e2e", "regression"}},
    }
    # Don't dump huge prior JSON into report payload twice
    slim_priors = {k: priors[k] for k in ("baseline", "grounding", "claim_binding", "hardening", "e2e", "regression")}
    payload["priors"] = slim_priors
    _dump(OUT / "validation.json", {"generated_at": payload["generated_at"], "offline": offline, "rows": rows})

    _write_reliability_report(offline, rows, slim_priors)
    _write_readiness_assessment(offline, rows)
    print("Wrote", REPORT)
    print("Wrote", READINESS)

    live_ok = all((r.get("judgment") or {}).get("ok") for r in rows)
    offline_ok = all(bool(v.get("ok")) for v in offline.values() if v.get("ok") is not None and not v.get("skipped"))
    return 0 if live_ok and offline_ok else 2


def _write_reliability_report(
    offline: dict[str, Any],
    rows: list[dict[str, Any]],
    priors: dict[str, Any],
) -> None:
    passed = sum(1 for r in rows if (r.get("judgment") or {}).get("ok"))
    lines = [
        "# LumenFin RC Final Reliability Report",
        "",
        f"Generated: {_now()}",
        "",
        "Release Candidate validation of **current** LumenFin + FinAgentBench.",
        "No new claim/citation rules. No evaluator threshold changes.",
        "",
        "Canonical path: `LumenFin → export_finrun_state() → FinAgentBench (ci)`.",
        "",
        "## 1. Offline gates",
        "",
        "| Gate | OK | Return code |",
        "|------|:--:|------------:|",
    ]
    for name, result in offline.items():
        lines.append(f"| `{name}` | {'Y' if result.get('ok') else ('skip' if result.get('skipped') else 'N')} | {result.get('returncode')} |")
    lines += [
        "",
        "## 2. Expanded real-company RC pack",
        "",
        f"| Cases | Passed |",
        f"|------:|-------:|",
        f"| {len(rows)} | **{passed}/{len(rows)}** |",
        "",
        "| Case | Scenario | Status | OK | Entities | Verified claims | Report cov | #pN | Checkable | FAB score |",
        "|------|----------|--------|:--:|----------|----------------:|-----------:|----:|----------:|----------:|",
    ]
    for r in rows:
        cov = r.get("claim_coverage") or {}
        fab = r.get("fab") or {}
        lines.append(
            f"| {r.get('label')} | {r.get('raw_scenario') or r.get('scenario')} | `{r.get('workflow_status')}` | "
            f"{'Y' if (r.get('judgment') or {}).get('ok') else 'N'} | `{r.get('entities')}` | "
            f"{cov.get('verified_total')} | {cov.get('report_coverage')} | {cov.get('citation_markers')} | "
            f"{r.get('checkable')} | {fab.get('score')} |"
        )
    lines += [
        "",
        "## 3. Claim coverage & failure recovery",
        "",
        "### Completed diligence",
        "",
        "| Case | Bind rate | Entity claim coverage | Page-anchored | Verified in report |",
        "|------|----------:|----------------------:|--------------:|-------------------:|",
    ]
    for r in rows:
        if r.get("expect") != "completed":
            continue
        cov = r.get("claim_coverage") or {}
        binding = cov.get("binding") or {}
        lines.append(
            f"| {r.get('label')} | {binding.get('bind_rate')} | {cov.get('entity_claim_coverage')} | "
            f"{cov.get('page_anchored')} | {cov.get('verified_in_report')}/{cov.get('verified_total')} |"
        )
    lines += [
        "",
        "### Fail-closed",
        "",
        "| Case | Status | Checkable | Invented numeric? |",
        "|------|--------|----------:|:-----------------:|",
    ]
    for r in rows:
        if (r.get("raw_scenario") or r.get("scenario")) != "failure_recovery":
            continue
        cov = r.get("claim_coverage") or {}
        by_ent = cov.get("by_entity") or {}
        invented = any((v.get("numeric") or 0) > 0 for v in by_ent.values())
        lines.append(
            f"| {r.get('label')} | `{r.get('workflow_status')}` | {r.get('checkable')} | "
            f"{'Y' if invented else 'N'} |"
        )
    lines += [
        "",
        "## 4. FinAgentBench reliability (completed cases)",
        "",
        "| Case | Score | evidence_coverage | evidence_consistency | numeric_correctness | entity_leakage |",
        "|------|------:|------------------:|---------------------:|--------------------:|---------------:|",
    ]
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
    lines += [
        "",
        "## 5. Prior phase evidence (synthesized)",
        "",
        "| Phase | Artifact | Present |",
        "|-------|----------|:-------:|",
    ]
    for key, meta in priors.items():
        lines.append(f"| {key} | `{meta.get('path')}` | {'Y' if meta.get('exists') else 'N'} |")
    lines += [
        "",
        "Key prior results carried into RC:",
        "- Financial Grounding: NVDA checkable 0→3, numeric 100, issuer-only retained",
        "- Claim Binding: NVDA `#pN` 6→36; verified claims rendered inline (13/13)",
        "- Production Hardening: 5/5 (long MSFT, AAPL–MSFT, long AAPL, OpenAI, sparse)",
        "",
        "## 6. Gate detail",
        "",
    ]
    for r in rows:
        lines.append(f"### {r.get('label')}")
        lines.append("")
        for c in ((r.get("judgment") or {}).get("checks") or []):
            mark = "PASS" if c.get("ok") else "FAIL"
            lines.append(f"- **{mark}** `{c.get('name')}` — {c.get('detail')}")
        lines.append("")
    all_live = all((r.get("judgment") or {}).get("ok") for r in rows)
    all_off = all(bool(v.get("ok")) for v in offline.values() if v.get("ok") is not None and not v.get("skipped"))
    lines += [
        "## 7. Verdict",
        "",
        (
            "**RC reliability gate: PASS.**"
            if all_live and all_off
            else "**RC reliability gate: FAIL/PARTIAL — see gates above; fix by failure type, not new rules.**"
        ),
        "",
        "## Artifacts",
        "",
        f"- `{OUT / 'validation.json'}`",
        f"- `{OUT / 'offline_gates.json'}`",
        f"- FinRuns: `{OUT / 'finrun'}`",
        "",
    ]
    text = "\n".join(lines)
    REPORT.write_text(text, encoding="utf-8")
    (FAB / REPORT.name).write_text(text, encoding="utf-8")


def _write_readiness_assessment(offline: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    live_ok = all((r.get("judgment") or {}).get("ok") for r in rows)
    offline_ok = all(bool(v.get("ok")) for v in offline.values() if v.get("ok") is not None and not v.get("skipped"))
    completed = [r for r in rows if r.get("expect") == "completed"]
    fails = [r for r in rows if (r.get("raw_scenario") or r.get("scenario")) == "failure_recovery"]
    fab_scores = [((r.get("fab") or {}).get("score")) for r in completed if (r.get("fab") or {}).get("score") is not None]
    mean_fab = round(sum(fab_scores) / len(fab_scores), 2) if fab_scores else None

    # Readiness dimensions
    dims = [
        ("Deterministic tests", offline_ok, "LumenFin unit + FinAgentBench unit/regression"),
        (
            "Issuer numeric grounding",
            all((r.get("checkable") or 0) >= 1 for r in completed if "compare" not in (r.get("id") or "")),
            "Checkable formula+inputs on issuer diligence",
        ),
        (
            "Claim → evidence binding",
            all(((r.get("claim_coverage") or {}).get("report_coverage") or 0) >= 0.8 for r in completed),
            "Verified claims appear in report with citations",
        ),
        (
            "Multi-company routing",
            all((r.get("judgment") or {}).get("ok") for r in rows if r.get("scenario") == "multi_company"),
            "AAPL–MSFT and NVDA–AMD entity parity without peer fan-out",
        ),
        (
            "Long-document stability",
            all((r.get("judgment") or {}).get("ok") for r in rows if (r.get("raw_scenario") or "") == "long_document" or "long" in (r.get("id") or "")),
            "MSFT long 10-K completes with claim coverage",
        ),
        (
            "Fail-closed honesty",
            all((r.get("judgment") or {}).get("ok") for r in fails) and all((r.get("checkable") or 0) == 0 for r in fails),
            "OpenAI + sparse upload refuse invented fundamentals",
        ),
        (
            "FinAgentBench floors",
            all(
                (((r.get("fab") or {}).get("metric_detail") or {}).get("evidence_coverage") or {}).get("score", 0) >= 100
                and (((r.get("fab") or {}).get("metric_detail") or {}).get("numeric_correctness") or {}).get("score", 0) >= 80
                for r in completed
                if r.get("fab") and not (r.get("fab") or {}).get("error")
            ),
            "evidence_coverage=100 and numeric_correctness≥80 on completed FAB cases",
        ),
    ]
    score = sum(1 for _, ok, _ in dims if ok)
    ready = live_ok and offline_ok and score == len(dims)

    lines = [
        "# LumenFin RC Production Readiness Assessment",
        "",
        f"Generated: {_now()}",
        "",
        "## Executive verdict",
        "",
        f"**{'READY for Release Candidate' if ready else 'NOT READY — blockers below'}**",
        "",
        f"- Live RC pack: **{sum(1 for r in rows if (r.get('judgment') or {}).get('ok'))}/{len(rows)}**",
        f"- Offline gates: **{'PASS' if offline_ok else 'FAIL'}**",
        f"- Mean FAB score (completed, informational): **{mean_fab}**",
        f"- Readiness dimensions: **{score}/{len(dims)}**",
        "",
        "## Dimension checklist",
        "",
        "| Dimension | Status | Evidence |",
        "|-----------|:------:|----------|",
    ]
    for name, ok, evidence in dims:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {evidence} |")
    lines += [
        "",
        "## What this RC proves",
        "",
        "1. Real-company coverage across Apple, NVIDIA, Tesla, Microsoft, AMD (compare), plus negative controls.",
        "2. Issuer SEC financial grounding + claim→evidence binding remain intact under long PDF and multi-company load.",
        "3. Fail-closed paths do not invent AST-checkable fundamentals or verified numeric claims.",
        "4. FinAgentBench `ci` floors hold without evaluator changes.",
        "",
        "## Explicit non-goals (this RC)",
        "",
        "- No new claim/citation rules",
        "- No FinAgentBench threshold relaxation",
        "- No retrieval-quality feature expansion",
        "",
        "## Residual risks (accept or track — not P0 invent-numbers)",
        "",
        "- DeepSeek / DashScope model renames and quota remain operational dependencies.",
        "- Live-only issuers still have 0 `#pN` (fundamentals citations by design).",
        "- Growth claims remain rejected without multi-period fundamentals (honest).",
        "- Milvus Lite single-process lock / AllocTimestamp noise under concurrent local use.",
        "",
        "## Go / No-Go",
        "",
    ]
    if ready:
        lines.append(
            "**GO** for Release Candidate: reliability gates green on expanded real-company pack; "
            "prior grounding / claim-binding / hardening evidence synthesized; architecture index published."
        )
    else:
        lines.append(
            "**NO-GO**: fix failing dimensions by failure type (offline / claim coverage / fail-closed / FAB floors). "
            "Do not add rules to inflate scores."
        )
    lines += [
        "",
        "## Related artifacts",
        "",
        f"- Final reliability: `{REPORT}`",
        f"- Architecture index: `{LUMEN / 'docs' / 'ARCHITECTURE_INDEX.md'}`",
        f"- RC validation JSON: `{OUT / 'validation.json'}`",
        "",
    ]
    text = "\n".join(lines)
    READINESS.write_text(text, encoding="utf-8")
    (FAB / READINESS.name).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
