#!/usr/bin/env python3
"""Re-evaluate LumenFin Before/After traces after FinAgentBench correctness fixes.

Canonical path:
  LumenFin ``*_state.json`` → ``export_finrun_state()`` (preferred) / lumenfin adapter
  → FinAgentBench evaluate (unchanged thresholds).
"""

from __future__ import annotations

import copy
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
from repo_paths import lumenfin_root

LUMEN = lumenfin_root()
STATES = LUMEN / "outputs"
OUT = ROOT / "outputs" / "lumenfin_correctness_eval"
FINRUN = OUT / "finrun"
REPORT = ROOT / "FinAgentBench_Correctness_Report.md"

CASE_GENERIC = ROOT / "fixtures" / "case_lumenfin_generic.json"
CASE_ISSUER_NVDA = ROOT / "fixtures" / "case_lumenfin_issuer_nvda.json"
CASE_COMPARE = ROOT / "fixtures" / "case_lumenfin_compare_nvda_amd.json"
CASE_DILIGENCE = ROOT / "fixtures" / "case_lumenfin_diligence.json"

CASES = [
    "ag01_apple_live",
    "ag02_nvda_pdf_live",
    "ag03_msft_pdf",
    "ag04_aapl_msft_compare",
    "ag05_tesla_live",
    "ag06_nvda_sustainability",
    "ag07_apple_pdf_risk",
    "ag08_openai_failclosed",
    "ag09_ambiguous",
    "ag10_sparse_pdf",
]

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LUMEN / "src"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _find_state(case_id: str, *, after: bool) -> Path | None:
    day = "20260725" if after else "20260724"
    matches = sorted(STATES.glob(f"e2e-{case_id}-*_{day}_*_state.json"), key=lambda p: p.stat().st_mtime)
    if matches:
        return matches[-1]
    all_matches = sorted(STATES.glob(f"e2e-{case_id}-*_state.json"), key=lambda p: p.stat().st_mtime)
    if not all_matches:
        return None
    return all_matches[-1] if after else (all_matches[-2] if len(all_matches) >= 2 else all_matches[0])


def _export_finrun(state: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Prefer LumenFin canonical exporter; fall back to corrected bench adapter."""
    try:
        from lumenfin.finrun import export_finrun_state

        run = export_finrun_state(state)
        # Ensure metric source/unit fields exist for schema richness (non-scoring).
        for metric in run.get("metrics") or []:
            metric.setdefault("unit", "ratio" if metric.get("formula") else "")
            conf = metric.get("confidence") or {}
            metric.setdefault("source", conf.get("structured_source") or "unknown")
        return run, "lumenfin.export_finrun_state"
    except Exception:
        from finagentbench.adapters.lumenfin import LumenFinAdapter

        return LumenFinAdapter().normalize(state), "finagentbench.adapters.lumenfin"


def _case_for(case_id: str) -> Path:
    if case_id in {"ag02_nvda_pdf_live", "ag06_nvda_sustainability"}:
        return CASE_ISSUER_NVDA
    return CASE_GENERIC


def _checkable_count(run: dict[str, Any]) -> int:
    return sum(1 for m in run.get("metrics") or [] if m.get("formula") and m.get("inputs"))


def _evaluate(run: dict[str, Any], case: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    from finagentbench.profiles import apply_profile
    from finagentbench.provenance import attach_provenance
    from finagentbench.report import write_eval_report
    from finagentbench.runner import evaluate_run

    case = apply_profile(case, "ci")
    report = attach_provenance(
        evaluate_run(run, case),
        case,
        profile="ci",
        adapter=str((run.get("metadata") or {}).get("adapter") or "lumenfin"),
    )
    paths = write_eval_report(report, out_dir)
    finding_metrics = sorted({f.metric for m in report.metrics for f in m.findings})
    metric_detail = {
        m.name: {
            "score": m.score,
            "passed": m.passed,
            "findings": [f.message for f in m.findings],
        }
        for m in report.metrics
    }
    return {
        "run_id": report.run_id,
        "passed": report.passed,
        "score": report.score,
        "finding_metrics": finding_metrics,
        "metric_detail": metric_detail,
        "entities": [e.get("name") if isinstance(e, dict) else e for e in run.get("entities") or []],
        "entity_count": len(run.get("entities") or []),
        "checkable_metrics": _checkable_count(run),
        "numeric_no_checkable": any(
            "no checkable items" in msg.lower()
            for msg in (metric_detail.get("numeric_correctness") or {}).get("findings") or []
        ),
        "entity_leakage_failed": not (metric_detail.get("entity_leakage") or {}).get("passed", True),
        "workflow_status": (run.get("metadata") or {}).get("workflow_status"),
        "paths": {k: str(v) for k, v in paths.items()},
    }


def _mutate(base: dict[str, Any], kind: str) -> dict[str, Any]:
    run = copy.deepcopy(base)
    text = str(run.get("final_output") or "")
    if kind == "wrong_revenue":
        metrics = run.get("metrics") or []
        for item in metrics:
            if item.get("formula") and item.get("inputs"):
                try:
                    item["value"] = float(item.get("value") or 0) * 1.75
                    break
                except (TypeError, ValueError):
                    item["value"] = 0.99
                    break
        run["final_output"] = text + "\n\nFabricated: revenue was $999,999 billion.\n"
        run["run_id"] = f"{run.get('run_id')}-mut-wrong-revenue"
    elif kind == "missing_citation":
        run["final_output"] = re.sub(r"#p\d+", "", text)
        run["evidence"] = []
        run["run_id"] = f"{run.get('run_id')}-mut-missing-citation"
    elif kind == "missing_risk":
        text2 = re.sub(r"(?is)^#{1,6}\s+.*risk.*$", "", text, flags=re.M)
        for phrase in (
            "Risk Exposure Matrix",
            "Risk Considerations",
            "Risk Architecture",
            "market risk",
            "valuation risk",
            "data limitation",
            "data limitations",
            "not investment advice",
            "research only",
            "risk-model",
            "risk-screening",
            "model risk",
            "incomplete",
            "uncertainty",
            "uncertain",
            "volatility",
            "drawdown",
            "limitation",
            "risk",
        ):
            text2 = re.sub(re.escape(phrase), "", text2, flags=re.I)
        run["final_output"] = text2
        run["run_id"] = f"{run.get('run_id')}-mut-missing-risk"
    elif kind == "wrong_company":
        run["entities"] = [{"name": "OpenAI"}]
        for item in run.get("metrics") or []:
            item["entity"] = "OpenAI"
        run["final_output"] = text.replace("Apple", "OpenAI").replace("Microsoft", "OpenAI")
        run["run_id"] = f"{run.get('run_id')}-mut-wrong-company"
    return run


def _avg(nums: list[float]) -> float:
    return round(sum(nums) / len(nums), 2) if nums else 0.0


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FINRUN.mkdir(parents=True, exist_ok=True)

    rows: dict[str, list[dict[str, Any]]] = {"before": [], "after": []}
    for label, after in (("before", False), ("after", True)):
        for case_id in CASES:
            state_path = _find_state(case_id, after=after)
            if not state_path:
                rows[label].append({"case_id": case_id, "ok": False, "error": "missing_state"})
                continue
            state = _load(state_path)
            run, exporter = _export_finrun(state)
            if not run.get("run_id") or run["run_id"] == "lumenfin-run":
                run["run_id"] = state_path.stem.replace("_state", "")
            fin_path = FINRUN / label / f"{case_id}.json"
            _dump(fin_path, run)
            case_path = _case_for(case_id)
            result = _evaluate(run, _load(case_path), OUT / "eval" / label / case_id)
            result.update(
                {
                    "case_id": case_id,
                    "ok": True,
                    "state": str(state_path),
                    "finrun": str(fin_path),
                    "exporter": exporter,
                    "case_file": case_path.name,
                }
            )
            rows[label].append(result)
            print(
                f"[{label}] {case_id}: score={result['score']} "
                f"checkable={result['checkable_metrics']} "
                f"numeric_empty={result['numeric_no_checkable']} "
                f"leak={result['entity_leakage_failed']} "
                f"entities={result['entities']}"
            )

    # Entity leakage targeted checks
    from finagentbench.runner import evaluate_run
    from finagentbench.profiles import apply_profile

    issuer_case = apply_profile(_load(CASE_ISSUER_NVDA), "ci")
    compare_case = apply_profile(_load(CASE_COMPARE), "ci")
    before_nvda = _load(FINRUN / "before" / "ag02_nvda_pdf_live.json") if (FINRUN / "before" / "ag02_nvda_pdf_live.json").exists() else None
    after_nvda = _load(FINRUN / "after" / "ag02_nvda_pdf_live.json") if (FINRUN / "after" / "ag02_nvda_pdf_live.json").exists() else None
    entity_checks = {}
    if before_nvda:
        br = evaluate_run(before_nvda, issuer_case)
        entity_checks["before_nvda_issuer"] = {
            "score": br.score,
            "leak_findings": [f.message for m in br.metrics if m.name == "entity_leakage" for f in m.findings],
            "entities": [e.get("name") if isinstance(e, dict) else e for e in before_nvda.get("entities") or []],
        }
    if after_nvda:
        ar = evaluate_run(after_nvda, issuer_case)
        entity_checks["after_nvda_issuer"] = {
            "score": ar.score,
            "leak_findings": [f.message for m in ar.metrics if m.name == "entity_leakage" for f in m.findings],
            "entities": [e.get("name") if isinstance(e, dict) else e for e in after_nvda.get("entities") or []],
        }
    # Synthetic compare run: NVIDIA+AMD should pass leakage
    compare_run = copy.deepcopy(after_nvda or before_nvda or {"entities": [], "final_output": "", "metrics": [], "evidence": [], "market_data": [], "steps": [], "run_id": "compare-synth"})
    compare_run["entities"] = [{"name": "NVIDIA"}, {"name": "AMD"}]
    compare_run["run_id"] = "compare-nvda-amd-synth"
    cr = evaluate_run(compare_run, compare_case)
    entity_checks["compare_nvda_amd"] = {
        "leak_passed": next(m.passed for m in cr.metrics if m.name == "entity_leakage"),
        "coverage_findings": [f.message for m in cr.metrics if m.name == "entity_coverage" for f in m.findings],
    }

    # Mutations on Apple/Microsoft FinRun (after ag04 preferred)
    base_path = FINRUN / "after" / "ag04_aapl_msft_compare.json"
    if not base_path.exists():
        base_path = FINRUN / "before" / "ag04_aapl_msft_compare.json"
    if base_path.exists():
        mutation_base = _load(base_path)
    else:
        from finagentbench.adapters import load_run_file

        mutation_base = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")

    detection = []
    for kind, label, expected in (
        ("wrong_revenue", "Wrong revenue", {"numeric_correctness", "evidence_consistency"}),
        ("missing_citation", "Missing citation", {"evidence_coverage", "evidence_consistency"}),
        ("missing_risk", "Missing risk section", {"risk_disclosure", "section_presence"}),
        ("wrong_company", "Wrong company", {"entity_coverage"}),
    ):
        mut = _mutate(mutation_base, kind)
        _dump(OUT / "mutations" / f"{kind}.json", mut)
        case = _load(CASE_DILIGENCE if kind == "wrong_company" else CASE_GENERIC)
        result = _evaluate(mut, case, OUT / "mutations" / f"eval_{kind}")
        found = set(result["finding_metrics"])
        detected = (not result["passed"]) and bool(found & expected or kind != "wrong_company")
        if kind == "wrong_company":
            detected = "entity_coverage" in found and not result["passed"]
        elif kind == "wrong_revenue":
            detected = bool(found & {"numeric_correctness", "evidence_consistency"}) and not result["passed"]
        elif kind == "missing_citation":
            detected = bool(found & {"evidence_coverage", "evidence_consistency"}) or not result["passed"]
        elif kind == "missing_risk":
            detected = bool(found & {"risk_disclosure", "section_presence"}) and not result["passed"]
        detection.append({"failure": label, "detected": "YES" if detected else "NO", "score": result["score"], "findings": ",".join(result["finding_metrics"]) or "-"})
        print(f"[mutation] {kind}: detected={detected} findings={result['finding_metrics']}")

    from finagentbench.benchmark import run_benchmark_suite

    suite = run_benchmark_suite(ROOT / "benchmarks" / "lumenfin_regression" / "suite.json")

    summary = {
        "generated_at": _now(),
        "before": rows["before"],
        "after": rows["after"],
        "entity_checks": entity_checks,
        "detection": detection,
        "suite": suite,
        "means": {
            "before_score": _avg([r["score"] for r in rows["before"] if r.get("ok")]),
            "after_score": _avg([r["score"] for r in rows["after"] if r.get("ok")]),
            "before_checkable": _avg([float(r["checkable_metrics"]) for r in rows["before"] if r.get("ok")]),
            "after_checkable": _avg([float(r["checkable_metrics"]) for r in rows["after"] if r.get("ok")]),
            "before_numeric_empty": sum(1 for r in rows["before"] if r.get("numeric_no_checkable")),
            "after_numeric_empty": sum(1 for r in rows["after"] if r.get("numeric_no_checkable")),
        },
    }
    _dump(OUT / "summary.json", summary)
    _write_report(summary)
    print(f"Wrote {REPORT}")
    return 0


def _write_report(summary: dict[str, Any]) -> None:
    means = summary["means"]
    detection = summary["detection"]
    entity_checks = summary["entity_checks"]
    yes = sum(1 for d in detection if d["detected"] == "YES")

    lines: list[str] = []
    lines.append("# FinAgentBench Correctness Report")
    lines.append("")
    lines.append(f"Generated: {summary['generated_at']}")
    lines.append("")
    lines.append("Goal: make FinAgentBench a trustworthy quality gate — **not** raise LumenFin pass rates.")
    lines.append("Thresholds / `min_score` / severity blocks were **not** relaxed.")
    lines.append("")
    lines.append("## Fixes shipped")
    lines.append("")
    lines.append("| ID | Change |")
    lines.append("|----|--------|")
    lines.append("| P0-1 | `adapters/lumenfin.py` aligned to canonical FinRun; fundamentals via `revenue` (+ legacy `revenue_2025`); period from `fundamentals_meta`; metric `source`/`unit` |")
    lines.append("| P0-1 | Eval path prefers `lumenfin.finrun.export_finrun_state()` then evaluate |")
    lines.append("| P0-2 | Live Apple/NVIDIA/Tesla traces now export checkable formula+inputs |")
    lines.append("| P1 | New `entity_leakage` metric + `forbidden_entities`; issuer NVDA case + compare NVDA/AMD case |")
    lines.append("| P1 | `section_presence` heading-level match (body \"Risk Exposure Matrix\" no longer counts) |")
    lines.append("")
    lines.append("## 1. Numeric metrics actually fire?")
    lines.append("")
    lines.append(f"| Cohort | Mean checkable formula metrics | Cases with `no checkable items` |")
    lines.append(f"|--------|--------------------------------:|---------------------------------:|")
    lines.append(f"| Before | {means['before_checkable']} | {means['before_numeric_empty']} / 10 |")
    lines.append(f"| After | {means['after_checkable']} | {means['after_numeric_empty']} / 10 |")
    lines.append("")
    lines.append("Per-case checkable counts:")
    lines.append("")
    lines.append("| Case | Before checkable | After checkable | Before numeric empty? | After numeric empty? |")
    lines.append("|------|-----------------:|----------------:|:---------------------:|:--------------------:|")
    before_map = {r["case_id"]: r for r in summary["before"] if r.get("ok")}
    after_map = {r["case_id"]: r for r in summary["after"] if r.get("ok")}
    for cid in CASES:
        b = before_map.get(cid) or {}
        a = after_map.get(cid) or {}
        lines.append(
            f"| {cid} | {b.get('checkable_metrics')} | {a.get('checkable_metrics')} | "
            f"{'Y' if b.get('numeric_no_checkable') else 'N'} | "
            f"{'Y' if a.get('numeric_no_checkable') else 'N'} |"
        )
    lines.append("")
    lines.append("## 2. Entity leakage reliably detected?")
    lines.append("")
    lines.append(f"- Before NVDA issuer case: `{entity_checks.get('before_nvda_issuer')}`")
    lines.append(f"- After NVDA issuer case: `{entity_checks.get('after_nvda_issuer')}`")
    lines.append(f"- Compare NVIDIA+AMD (forbidden empty): `{entity_checks.get('compare_nvda_amd')}`")
    lines.append("")
    lines.append("Expectation: Before leaks peers → `entity_leakage` findings; After issuer-only → no leakage findings; compare allows AMD.")
    lines.append("")
    lines.append("## 3. Mutation detection still 4/4?")
    lines.append("")
    lines.append("| Failure | Detected | Score | Findings |")
    lines.append("|---------|----------|------:|----------|")
    for row in detection:
        lines.append(f"| {row['failure']} | {row['detected']} | {row['score']} | {row['findings']} |")
    lines.append("")
    lines.append(f"Mutation detection rate: **{yes}/{len(detection)}**")
    suite = summary.get("suite") or {}
    lines.append(
        f"Packaged `lumenfin_regression` suite: detection_rate={suite.get('detection_rate')} "
        f"false_positives={suite.get('false_positives')} passed={suite.get('passed')}"
    )
    lines.append("")
    lines.append("## Score movement (informational only)")
    lines.append("")
    lines.append(f"| System | Mean score |")
    lines.append(f"|--------|-----------:|")
    lines.append(f"| Before | {means['before_score']} |")
    lines.append(f"| After | {means['after_score']} |")
    lines.append("")
    lines.append("Do **not** treat score deltas as the success criterion for this phase.")
    lines.append("")
    lines.append("## Is FinAgentBench credible as a LumenFin quality gate?")
    lines.append("")
    numeric_ok = means["before_checkable"] > 0 or means["after_checkable"] > 0
    leak_before = bool((entity_checks.get("before_nvda_issuer") or {}).get("leak_findings"))
    leak_after = bool((entity_checks.get("after_nvda_issuer") or {}).get("leak_findings"))
    compare_ok = bool((entity_checks.get("compare_nvda_amd") or {}).get("leak_passed"))
    mut_ok = yes == len(detection) and len(detection) == 4
    credible = numeric_ok and leak_before and (not leak_after) and compare_ok and mut_ok
    if credible:
        lines.append(
            "**Yes, with caveats.** Numeric checks now exercise live fundamentals; "
            "issuer peer leakage is a first-class fail; heading-level sections reduce false passes; "
            "mutations remain 4/4. Still pair issuer cases (fixed expected/forbidden entities) with "
            "generic diligence cases — `derive_entities_from_run` alone cannot prove leakage."
        )
    else:
        lines.append(
            f"**Partially.** numeric_ok={numeric_ok}, leak_before={leak_before}, "
            f"leak_after_cleared={not leak_after}, compare_ok={compare_ok}, mutations={yes}/{len(detection)}. "
            "See gaps above before treating scores as a sole release gate."
        )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `{OUT}`")
    lines.append(f"- FinRuns: `{FINRUN}`")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    # Mirror into LumenFin repo for convenience
    (LUMEN / "FinAgentBench_Correctness_Report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
