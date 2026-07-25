#!/usr/bin/env python3
"""Release Candidate Validation — expand real-company coverage + reliability gates.

Import of this module is side-effect free:
- no cwd changes
- no dotenv loading
- no Agent / Milvus / DB / network initialization
- no subprocesses

Heavy work runs only from main() after explicit CLI selection.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Standard-library-only top level. Repo discovery helpers are pure Path lookups.
from repo_paths import finagentbench_root, lumenfin_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _rc_cases(lumen: Path, fab: Path) -> list[dict[str, Any]]:
    """Build RC case specs with repository-relative fixture paths."""
    fix = lumen / "tests" / "fixtures" / "sec" / "derived"
    # Prefer manifested excerpts; fall back to ignored local e2e_real if present.
    legacy = lumen / "fixtures" / "e2e_real"
    stress = lumen / "fixtures" / "stress"

    def pdf(*candidates: Path) -> Path:
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    return [
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
            "case": fab / "fixtures" / "case_lumenfin_issuer_aapl.json",
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
            "docs": [
                pdf(
                    fix / "nvda_fy2025_10k_excerpt.pdf",
                    legacy / "nvda_fy2025_10k_sec.pdf",
                )
            ],
            "case": fab / "fixtures" / "case_lumenfin_issuer_nvda.json",
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
            "case": fab / "fixtures" / "case_lumenfin_issuer_tsla.json",
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
            "docs": [
                pdf(
                    fix / "msft_fy2024_10k_long_excerpt.pdf",
                    legacy / "msft_fy2024_10k_sec_long.pdf",
                )
            ],
            "case": fab / "fixtures" / "case_lumenfin_issuer_msft.json",
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
            "case": fab / "fixtures" / "case_lumenfin_compare_aapl_msft.json",
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
            "case": fab / "fixtures" / "case_lumenfin_compare_nvda_amd.json",
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
            "docs": [stress / "oracle_sparse_fluff.pdf"],
            "case": None,
        },
    ]


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 600) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-1500:],
            "stderr_tail": (proc.stderr or "")[-1500:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": -1,
            "error": f"TimeoutExpired after {timeout}s: {' '.join(cmd)}",
            "stdout_tail": ((exc.stdout or "") if isinstance(exc.stdout, str) else "")[-1500:],
            "stderr_tail": ((exc.stderr or "") if isinstance(exc.stderr, str) else "")[-1500:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "returncode": -1, "error": str(exc)}


def _validate_claim_binder_steps(fab: Path) -> None:
    missing: list[str] = []
    for name in (
        "case_lumenfin_diligence.json",
        "case_lumenfin_issuer_aapl.json",
        "case_lumenfin_issuer_nvda.json",
        "case_lumenfin_issuer_msft.json",
        "case_lumenfin_issuer_tsla.json",
        "case_lumenfin_compare_aapl_msft.json",
        "case_lumenfin_compare_nvda_amd.json",
    ):
        path = fab / "fixtures" / name
        if not path.exists():
            missing.append(name)
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        steps = list(case.get("required_steps") or [])
        if "claim_binder" not in steps:
            missing.append(name)
    if missing:
        raise RuntimeError(
            "Fixtures missing required claim_binder step (no runtime mutation allowed): "
            + ", ".join(missing)
        )


def _run_offline_gates(lumen: Path, fab: Path, out: Path) -> dict[str, Any]:
    py = sys.executable
    unit = _run_cmd([py, str(lumen / "scripts" / "run_tests.py")], cwd=lumen, timeout=300)
    fab_tests = _run_cmd(
        [py, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=fab,
        timeout=300,
    )
    fab_suite = fab / "benchmarks" / "lumenfin_regression" / "suite.json"
    if fab_suite.exists():
        fab_bench = _run_cmd(
            [
                py,
                "-m",
                "finagentbench",
                "benchmark",
                str(fab_suite),
                "--out",
                str(out / "fab_lumenfin_regression.json"),
            ],
            cwd=fab,
            timeout=300,
        )
    else:
        fab_bench = {"ok": None, "skipped": True, "returncode": None}
    correctness = fab / "scripts" / "run_correctness_validation.py"
    if correctness.exists():
        fab_correct = _run_cmd([py, str(correctness)], cwd=fab, timeout=300)
    else:
        fab_correct = {"ok": None, "skipped": True, "returncode": None}
    return {
        "lumenfin_unit": unit,
        "finagentbench_unit": fab_tests,
        "finagentbench_lumenfin_regression": fab_bench,
        "finagentbench_correctness": fab_correct,
    }


def _run_live_case(
    *,
    lumen: Path,
    out: Path,
    spec: dict[str, Any],
    expected_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Deferred import: keeps module import free of Agent/provider side effects.
    import rc_runtime as runtime

    docs = [Path(d) for d in (spec.get("docs") or [])]
    missing = [str(d) for d in docs if not d.exists()]
    if missing:
        row = {
            "id": spec["id"],
            "label": spec["label"],
            "scenario": "failure_recovery" if spec["scenario"] == "failure_recovery" else spec["scenario"],
            "raw_scenario": spec["scenario"],
            "expect": spec["expect"],
            "expect_entities": spec.get("expect_entities"),
            "workflow_status": "crashed",
            "error": f"missing fixture(s): {missing}",
            "entities": [],
            "checkable": 0,
            "elapsed_ms": 0.0,
            "claim_coverage": {},
            "fab": None,
            "llm_backend": None,
            "llm_model": None,
        }
        row["judgment"] = runtime.judge_row(row)
        return row

    state, elapsed_ms, err = runtime.live_analyze(
        lumen_root=lumen,
        out_dir=out,
        query=spec["query"],
        docs=docs,
        prefix=f"rc-{spec['id']}",
        expected_fingerprint=expected_fingerprint,
    )
    runtime.dump_json(out / "states" / f"{spec['id']}_state.json", state)
    run = (
        runtime.export_finrun(state)
        if state.get("workflow_status") != "crashed"
        else {}
    )
    if state.get("workflow_status") != "crashed":
        runtime.dump_json(out / "finrun" / f"{spec['id']}.json", run)

    final_output = str(run.get("final_output") or state.get("final_report") or "")
    cov = (
        runtime.claim_coverage(state, final_output)
        if state.get("workflow_status") != "crashed"
        else {}
    )
    fab = None
    if spec.get("case") and state.get("workflow_status") == "completed":
        try:
            fab = runtime.evaluate_finrun(run, Path(spec["case"]), out / "eval" / spec["id"])
        except Exception as exc:  # noqa: BLE001
            fab = {"error": str(exc)}

    metrics = run.get("metrics") or []
    checkable = sum(
        1
        for item in metrics
        if item.get("formula") and isinstance(item.get("inputs"), dict) and item.get("inputs")
    )
    row = {
        "id": spec["id"],
        "label": spec["label"],
        "scenario": (
            "multi_company"
            if spec["scenario"] == "multi_company"
            else (
                "failure_recovery"
                if spec["scenario"] == "failure_recovery"
                else (
                    "long_document"
                    if spec["scenario"] == "long_document"
                    else "issuer_live"
                )
            )
        ),
        "raw_scenario": spec["scenario"],
        "expect": spec["expect"],
        "expect_entities": spec.get("expect_entities"),
        "workflow_status": state.get("workflow_status"),
        "error": err,
        "entities": list(state.get("companies") or []),
        "checkable": checkable,
        "elapsed_ms": elapsed_ms,
        "claim_coverage": cov,
        "fab": fab,
        "llm_backend": state.get("llm_backend"),
        "llm_model": state.get("llm_model"),
    }
    row["judgment"] = runtime.judge_row(row)
    print(
        f"[{spec['id']}] status={row['workflow_status']} ok={row['judgment']['ok']} "
        f"backend={row['llm_backend']} model={row['llm_model']} "
        f"verified={cov.get('verified_total')} fab={((fab or {}).get('score'))} "
        f"elapsed_ms={row['elapsed_ms']}",
        flush=True,
    )
    return row


def _load_prior_summaries(lumen: Path, fab: Path) -> dict[str, Any]:
    priors: dict[str, Any] = {}
    history = lumen / "reports" / "history"
    current = lumen / "reports" / "current"
    mapping = {
        "baseline": history / "LumenFin_Final_Reliability_Baseline.md",
        "grounding": history / "LumenFin_Financial_Grounding_Validation.md",
        "claim_binding": history / "LumenFin_Claim_Evidence_Binding_Report.md",
        "hardening": history / "LumenFin_Production_Hardening_Report.md",
        "e2e": history / "LumenFin_E2E_Audit_Report.md",
        "regression": history / "LumenFin_Regression_Comparison.md",
        "rc_current": current / "LumenFin_RC_Final_Reliability_Report.md",
    }
    for key, path in mapping.items():
        # Fall back to ignored root copies for local workstations.
        alt = lumen / path.name
        chosen = path if path.exists() else alt
        priors[key] = {"exists": chosen.exists(), "path": str(chosen)}
    for key, path in {
        "hardening_json": fab / "outputs" / "lumenfin_production_hardening" / "validation.json",
        "claim_json": fab / "outputs" / "lumenfin_claim_binding" / "validation.json",
        "grounding_json": fab / "outputs" / "lumenfin_financial_grounding" / "validation.json",
    }.items():
        if path.exists():
            priors[key] = json.loads(path.read_text(encoding="utf-8"))
    return priors


def _dry_run(lumen: Path, fab: Path) -> int:
    print("=== RC DRY-RUN (no live APIs, no Agent init) ===", flush=True)
    print(f"lumenfin={lumen}")
    print(f"finagentbench={fab}")
    _validate_claim_binder_steps(fab)
    cases = _rc_cases(lumen, fab)
    missing_docs = []
    for spec in cases:
        for doc in spec.get("docs") or []:
            if not Path(doc).exists():
                missing_docs.append(str(doc))
    print(f"cases={len(cases)}")
    if missing_docs:
        print("missing_docs:")
        for item in missing_docs:
            print(f"  - {item}")
        print("dry-run: PARTIAL (paths/schema checked; PDF fixtures missing)")
        return 3
    print("dry-run: PASS (paths + claim_binder schema)")
    return 0


def _write_reliability_report(
    *,
    report: Path,
    fab: Path,
    out: Path,
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
        lines.append(
            f"| `{name}` | "
            f"{'Y' if result.get('ok') else ('skip' if result.get('skipped') else 'N')} | "
            f"{result.get('returncode')} |"
        )
    lines += [
        "",
        "## 2. Expanded real-company RC pack",
        "",
        "| Cases | Passed |",
        "|------:|-------:|",
        f"| {len(rows)} | **{passed}/{len(rows)}** |",
        "",
        "| Case | Scenario | Status | OK | Entities | Verified claims | Report cov | #pN | Checkable | FAB score |",
        "|------|----------|--------|:--:|----------|----------------:|-----------:|----:|----------:|----------:|",
    ]
    for r in rows:
        cov = r.get("claim_coverage") or {}
        fab_row = r.get("fab") or {}
        lines.append(
            f"| {r.get('label')} | {r.get('raw_scenario') or r.get('scenario')} | "
            f"`{r.get('workflow_status')}` | "
            f"{'Y' if (r.get('judgment') or {}).get('ok') else 'N'} | `{r.get('entities')}` | "
            f"{cov.get('verified_total')} | {cov.get('report_coverage')} | "
            f"{cov.get('citation_markers')} | {r.get('checkable')} | {fab_row.get('score')} |"
        )
    all_live = all((r.get("judgment") or {}).get("ok") for r in rows)
    all_off = all(
        bool(v.get("ok"))
        for v in offline.values()
        if v.get("ok") is not None and not v.get("skipped")
    )
    lines += [
        "",
        "## 3. Verdict",
        "",
        (
            "**RC reliability gate: PASS.**"
            if all_live and all_off
            else "**RC reliability gate: FAIL/PARTIAL — see gates above.**"
        ),
        "",
        "## Artifacts",
        "",
        f"- `{out / 'validation.json'}`",
        f"- `{out / 'offline_gates.json'}`",
        "",
        "## Prior phase evidence",
        "",
        "| Phase | Artifact | Present |",
        "|-------|----------|:-------:|",
    ]
    for key, meta in priors.items():
        lines.append(
            f"| {key} | `{meta.get('path')}` | {'Y' if meta.get('exists') else 'N'} |"
        )
    text = "\n".join(lines) + "\n"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text, encoding="utf-8")
    (fab / "reports" / "current" / report.name).parent.mkdir(parents=True, exist_ok=True)
    (fab / "reports" / "current" / report.name).write_text(text, encoding="utf-8")


def _write_readiness_assessment(
    *,
    readiness: Path,
    fab: Path,
    report: Path,
    out: Path,
    offline: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    live_ok = all((r.get("judgment") or {}).get("ok") for r in rows)
    offline_ok = all(
        bool(v.get("ok"))
        for v in offline.values()
        if v.get("ok") is not None and not v.get("skipped")
    )
    completed = [r for r in rows if r.get("expect") == "completed"]
    fab_scores = [
        ((r.get("fab") or {}).get("score"))
        for r in completed
        if (r.get("fab") or {}).get("score") is not None
    ]
    mean_fab = round(sum(fab_scores) / len(fab_scores), 2) if fab_scores else None
    lines = [
        "# LumenFin RC Production Readiness Assessment",
        "",
        f"Generated: {_now()}",
        "",
        "## Executive verdict",
        "",
        f"**{'READY for Release Candidate' if live_ok and offline_ok else 'NOT READY — blockers below'}**",
        "",
        f"- Live RC pack: **{sum(1 for r in rows if (r.get('judgment') or {}).get('ok'))}/{len(rows)}**",
        f"- Offline gates: **{'PASS' if offline_ok else 'FAIL'}**",
        f"- Mean FAB score (completed, informational): **{mean_fab}**",
        "",
        f"- Final reliability: `{report}`",
        f"- RC validation JSON: `{out / 'validation.json'}`",
        "",
    ]
    text = "\n".join(lines)
    readiness.parent.mkdir(parents=True, exist_ok=True)
    readiness.write_text(text, encoding="utf-8")
    (fab / "reports" / "current" / readiness.name).parent.mkdir(parents=True, exist_ok=True)
    (fab / "reports" / "current" / readiness.name).write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="LumenFin + FinAgentBench Release Candidate validation runner",
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Run offline unit/regression/correctness gates only (no live Agent calls).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check repository paths, fixtures and claim_binder schema without running gates.",
    )
    args = parser.parse_args(argv)

    lumen = lumenfin_root()
    fab = finagentbench_root()
    out = fab / "outputs" / "lumenfin_rc_validation"
    report = lumen / "reports" / "current" / "LumenFin_RC_Final_Reliability_Report.md"
    readiness = lumen / "reports" / "current" / "LumenFin_RC_Production_Readiness_Assessment.md"

    if args.dry_run:
        return _dry_run(lumen, fab)

    _validate_claim_binder_steps(fab)
    out.mkdir(parents=True, exist_ok=True)

    print("=== OFFLINE GATES ===", flush=True)
    offline = _run_offline_gates(lumen, fab, out)
    _dump(out / "offline_gates.json", offline)
    for name, result in offline.items():
        print(
            f"  {name}: ok={result.get('ok')} rc={result.get('returncode')}",
            flush=True,
        )

    if args.offline_only:
        offline_ok = all(
            bool(v.get("ok"))
            for v in offline.values()
            if v.get("ok") is not None and not v.get("skipped")
        )
        return 0 if offline_ok else 2

    print("=== LIVE RC PREFLIGHT (shared AppConfig path) ===", flush=True)
    # Formal live path imports LumenFin via the same src tree as AppConfig.
    lumen_src = str(lumen / "src")
    if lumen_src not in sys.path:
        sys.path.insert(0, lumen_src)
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import rc_runtime as runtime

    try:
        preflight = runtime.live_preflight(lumen_root=lumen)
    except Exception as exc:  # noqa: BLE001
        print(f"LIVE RC PREFLIGHT FAILED: {exc}", flush=True)
        return 2
    expected_fingerprint = preflight["fingerprint"]
    _dump(out / "preflight.json", {"generated_at": _now(), "fingerprint": expected_fingerprint})

    print("=== LIVE RC PACK ===", flush=True)
    rows: list[dict[str, Any]] = []
    for spec in _rc_cases(lumen, fab):
        try:
            row = _run_live_case(
                lumen=lumen,
                out=out,
                spec=spec,
                expected_fingerprint=expected_fingerprint,
            )
        except runtime.LocalFallbackAbort as exc:
            print(f"ABORT: {exc}", flush=True)
            rows.append(
                {
                    "id": spec["id"],
                    "label": spec["label"],
                    "scenario": spec["scenario"],
                    "raw_scenario": spec["scenario"],
                    "expect": spec["expect"],
                    "workflow_status": "crashed",
                    "error": str(exc),
                    "entities": [],
                    "checkable": 0,
                    "elapsed_ms": 0.0,
                    "claim_coverage": {},
                    "fab": None,
                    "llm_backend": "local-fallback",
                    "llm_model": "local-fallback",
                    "judgment": {"ok": False, "checks": [{"name": "no_local_fallback", "ok": False}]},
                    "aborted": True,
                }
            )
            break
        rows.append(row)
        if row.get("llm_backend") == "local-fallback":
            print(f"ABORT: local-fallback on {spec['id']}", flush=True)
            break
    priors = _load_prior_summaries(lumen, fab)
    slim_priors = {
        k: priors[k]
        for k in (
            "baseline",
            "grounding",
            "claim_binding",
            "hardening",
            "e2e",
            "regression",
            "rc_current",
        )
        if k in priors
    }
    _dump(
        out / "validation.json",
        {"generated_at": _now(), "offline": offline, "rows": rows},
    )
    _write_reliability_report(
        report=report,
        fab=fab,
        out=out,
        offline=offline,
        rows=rows,
        priors=slim_priors,
    )
    _write_readiness_assessment(
        readiness=readiness,
        fab=fab,
        report=report,
        out=out,
        offline=offline,
        rows=rows,
    )
    print("Wrote", report)
    print("Wrote", readiness)

    live_ok = all((r.get("judgment") or {}).get("ok") for r in rows)
    offline_ok = all(
        bool(v.get("ok"))
        for v in offline.values()
        if v.get("ok") is not None and not v.get("skipped")
    )
    return 0 if live_ok and offline_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
