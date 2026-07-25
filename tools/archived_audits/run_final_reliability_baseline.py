#!/usr/bin/env python3
"""ARCHIVED AUDIT SCRIPT — unsupported release interface.

Historical purpose: produce the pre-RC LumenFin reliability baseline.
Replacement: scripts/run_rc_validation.py.
Last compatible schema: FinRun 1.0 transition.
Do not run against production fixtures.

Canonical path only:
  LumenFin state → lumenfin.finrun.export_finrun_state() → FinAgentBench evaluate

Does NOT modify FinAgentBench thresholds or LumenFin to chase scores.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from repo_paths import finagentbench_root, lumenfin_root

FAB = finagentbench_root()
LUMEN = lumenfin_root()
OUT = FAB / "outputs" / "lumenfin_final_baseline"
FINRUN = OUT / "finrun"
REPORT = LUMEN / "LumenFin_Final_Reliability_Baseline.md"
REPORT_FAB = FAB / "LumenFin_Final_Reliability_Baseline.md"

sys.path.insert(0, str(FAB))
sys.path.insert(0, str(LUMEN / "src"))

# Ensure LumenFin loads its .env
os.chdir(LUMEN)
try:
    from dotenv import load_dotenv

    load_dotenv(LUMEN / ".env")
except Exception:
    pass

CASE_GENERIC = FAB / "fixtures" / "case_lumenfin_generic.json"
CASE_ISSUER_NVDA = FAB / "fixtures" / "case_lumenfin_issuer_nvda.json"
CASE_ISSUER_TSLA = FAB / "fixtures" / "case_lumenfin_issuer_tsla.json"
CASE_ISSUER_AAPL = FAB / "fixtures" / "case_lumenfin_issuer_aapl.json"

NVDA_PDF = LUMEN / "fixtures" / "e2e_real" / "nvda_fy2025_10k_sec.pdf"
TSLA_PDF = LUMEN / "fixtures" / "e2e_real" / "tsla_fy2024_10k_sec.pdf"

BASELINE_CASES = [
    {
        "id": "apple_live",
        "label": "Apple live",
        "before_glob": "e2e-ag01_apple_live-*_20260724_*_state.json",
        "query": (
            "Analyze Apple FY2024 annual profitability, operating margin, and R&D intensity "
            "using live fundamentals. Discuss valuation context with current market snapshot."
        ),
        "docs": [],
        "case": CASE_ISSUER_AAPL,
        "rerun_live": True,
    },
    {
        "id": "nvidia_10k",
        "label": "NVIDIA 10-K",
        "before_glob": "e2e-ag02_nvda_pdf_live-*_20260724_*_state.json",
        "query": (
            "Analyze NVIDIA investment risk using the uploaded FY2025 10-K excerpt and "
            "current market valuation. Cite filing pages where possible."
        ),
        "docs": [str(NVDA_PDF)],
        "case": CASE_ISSUER_NVDA,
        "rerun_live": True,
    },
    {
        "id": "tesla_live",
        "label": "Tesla live",
        "before_glob": "e2e-ag05_tesla_live-*_20260724_*_state.json",
        "query": (
            "Analyze Tesla FY2024 profitability, automotive margin signals, and balance-sheet "
            "risk using live fundamentals and market data."
        ),
        "docs": [],
        "case": CASE_ISSUER_TSLA,
        "rerun_live": True,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_before(glob_pat: str) -> Path | None:
    matches = sorted((LUMEN / "outputs").glob(glob_pat), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def _export(state: dict[str, Any]) -> dict[str, Any]:
    from lumenfin.finrun import export_finrun_state

    run = export_finrun_state(state)
    for metric in run.get("metrics") or []:
        metric.setdefault("unit", "ratio" if metric.get("formula") else "")
        conf = metric.get("confidence") or {}
        metric.setdefault("source", conf.get("structured_source") or "unknown")
    return run


def _checkable(run: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in (run.get("metrics") or []) if m.get("formula") and m.get("inputs")]


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
        adapter="lumenfin-export",
    )
    paths = write_eval_report(report, out_dir)
    detail = {
        m.name: {
            "score": m.score,
            "passed": m.passed,
            "findings": [
                {"severity": f.severity, "message": f.message, "recommendation": f.recommendation}
                for f in m.findings
            ],
        }
        for m in report.metrics
    }
    return {
        "run_id": report.run_id,
        "passed": report.passed,
        "score": report.score,
        "metric_detail": detail,
        "entities": [e.get("name") if isinstance(e, dict) else e for e in run.get("entities") or []],
        "checkable": _checkable(run),
        "checkable_count": len(_checkable(run)),
        "evidence_count": len(run.get("evidence") or []),
        "steps": [s.get("name") for s in (run.get("steps") or [])],
        "workflow_status": (run.get("metadata") or {}).get("workflow_status"),
        "llm_backend": (run.get("metadata") or {}).get("llm_backend"),
        "paths": {k: str(v) for k, v in paths.items()},
        "final_output_chars": len(str(run.get("final_output") or "")),
        "citation_markers": str(run.get("final_output") or "").count("#p"),
    }


def _live_analyze(query: str, docs: list[str], thread_prefix: str) -> dict[str, Any]:
    from dataclasses import replace

    from lumenfin.config import AppConfig
    from lumenfin.service import LumenFinAnalysisService

    cfg = AppConfig.from_env()
    if not (cfg.llm.api_key or "").strip():
        raise RuntimeError("DEEPSEEK_API_KEY missing — refuse mock/fallback-only baseline")
    model = (cfg.llm.model or "").strip().lower()
    if model in {"", "deepseek-chat", "deepseek-reasoner"}:
        raise RuntimeError(
            f"DEEPSEEK_MODEL={cfg.llm.model!r} rejected by current DeepSeek API; "
            "set DEEPSEEK_MODEL=deepseek-v4-flash or deepseek-v4-pro"
        )
    if str(cfg.embedding_provider).lower() not in {"dashscope", "aliyun", "alibaba"}:
        print(f"WARN embedding_provider={cfg.embedding_provider}")

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
    thread_id = f"{thread_prefix}-{uuid4().hex[:8]}"
    print(f"LIVE analyze thread={thread_id} docs={docs or None}")
    pkg = service.analyze(
        query=query,
        document_paths=docs or None,
        thread_id=thread_id,
    )
    state = dict(pkg.get("result") or pkg)
    # Prefer on-disk state artifact if written
    artifacts = pkg.get("artifacts") or {}
    state_path = artifacts.get("state") or artifacts.get("state_path")
    if state_path and Path(state_path).exists():
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    else:
        # search outputs for newest matching thread
        matches = sorted(
            (LUMEN / "outputs").glob(f"{thread_id}*_state.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if matches:
            state = json.loads(matches[-1].read_text(encoding="utf-8"))
    state.setdefault("thread_id", thread_id)
    state.setdefault("run_id", thread_id)
    return state


def _ensure_issuer_cases() -> None:
    """Write Apple/Tesla issuer cases mirroring NVDA (no threshold changes)."""
    nvda = _load(CASE_ISSUER_NVDA)
    for path, company, forbidden_extra, q in (
        (
            CASE_ISSUER_AAPL,
            "Apple",
            ["Microsoft", "Alphabet", "Amazon", "NVIDIA", "Tesla", "Meta"],
            "Issuer-only gate for Apple live diligence.",
        ),
        (
            CASE_ISSUER_TSLA,
            "Tesla",
            ["Apple", "Microsoft", "NVIDIA", "Amazon", "Alphabet", "Ford", "GM"],
            "Issuer-only gate for Tesla live diligence.",
        ),
    ):
        if path.exists():
            continue
        case = dict(nvda)
        case["id"] = f"lumenfin_issuer_{company.lower()}_001"
        case["query"] = q
        case["expected_entities"] = [company]
        case["forbidden_entities"] = forbidden_extra
        _dump(path, case)


def _severity_rank(sev: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(sev, 9)


def _collect_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for row in rows:
        for metric, detail in (row.get("metric_detail") or {}).items():
            for finding in detail.get("findings") or []:
                failures.append(
                    {
                        "case": row.get("id"),
                        "cohort": row.get("cohort"),
                        "metric": metric,
                        "severity": finding.get("severity"),
                        "message": finding.get("message"),
                        "recommendation": finding.get("recommendation"),
                    }
                )
        if str(row.get("llm_backend") or "").startswith("local"):
            failures.append(
                {
                    "case": row.get("id"),
                    "cohort": row.get("cohort"),
                    "metric": "runtime_llm",
                    "severity": "high",
                    "message": f"llm_backend={row.get('llm_backend')} (DeepSeek degraded to local-fallback)",
                    "recommendation": "Stabilize primary LLM; treat local-fallback as release blocker for production baselines.",
                }
            )
        if row.get("workflow_status") == "incomplete_data" and row.get("id") in {
            "apple_live",
            "nvidia_10k",
            "tesla_live",
        }:
            failures.append(
                {
                    "case": row.get("id"),
                    "cohort": row.get("cohort"),
                    "metric": "runtime_workflow",
                    "severity": "high",
                    "message": "workflow_status=incomplete_data on core diligence case",
                    "recommendation": "Ensure issuer SEC fill or AST-computable upload metrics so quant completes without peer pollution.",
                }
            )
        if row.get("checkable_count", 0) == 0 and row.get("id") in {"apple_live", "tesla_live"}:
            failures.append(
                {
                    "case": row.get("id"),
                    "cohort": row.get("cohort"),
                    "metric": "financial_fact_coverage",
                    "severity": "high",
                    "message": "No checkable formula+inputs exported for live issuer case",
                    "recommendation": "Export formula-backed margins with market_data inputs for every completed live run.",
                }
            )
        if row.get("citation_markers", 0) == 0 and row.get("id") == "nvidia_10k" and row.get("workflow_status") == "completed":
            failures.append(
                {
                    "case": row.get("id"),
                    "cohort": row.get("cohort"),
                    "metric": "claim_citation_binding",
                    "severity": "medium",
                    "message": "NVIDIA 10-K completed report has zero #pN citation markers",
                    "recommendation": "Bind numeric/risk claims to retrieved page citations.",
                }
            )
    failures.sort(key=lambda f: (_severity_rank(str(f.get("severity"))), f.get("case") or "", f.get("metric") or ""))
    return failures


def main() -> int:
    _ensure_issuer_cases()
    OUT.mkdir(parents=True, exist_ok=True)
    FINRUN.mkdir(parents=True, exist_ok=True)

    from lumenfin.config import AppConfig

    cfg = AppConfig.from_env()
    if not (cfg.llm.api_key or "").strip():
        print("FAIL: DEEPSEEK_API_KEY required (no mock baseline)")
        return 1

    env_info = {
        "data_mode": cfg.data_mode,
        "llm_model": cfg.llm.model,
        "embedding_provider": cfg.embedding_provider,
        "fetch_sec": cfg.fetch_sec_fundamentals,
        "fetch_live": cfg.fetch_live_fundamentals,
        "started_at": _now(),
    }
    _dump(OUT / "env.json", env_info)
    print("ENV", env_info)

    results: list[dict[str, Any]] = []

    # --- Before: existing live audit states (already produced with real APIs) ---
    for spec in BASELINE_CASES:
        before_path = _find_before(spec["before_glob"])
        if not before_path:
            print("MISSING before", spec["before_glob"])
            continue
        state = _load(before_path)
        run = _export(state)
        run["run_id"] = f"before-{spec['id']}"
        _dump(FINRUN / "before" / f"{spec['id']}.json", run)
        case = _load(spec["case"])
        ev = _evaluate(run, case, OUT / "eval" / "before" / spec["id"])
        ev.update(
            {
                "id": spec["id"],
                "label": spec["label"],
                "cohort": "before",
                "state_path": str(before_path),
                "exporter": "lumenfin.finrun.export_finrun_state",
            }
        )
        results.append(ev)
        print(
            f"[before] {spec['id']}: score={ev['score']} checkable={ev['checkable_count']} "
            f"entities={ev['entities']} llm={ev['llm_backend']} status={ev['workflow_status']}"
        )

    # --- After: fresh live API runs on current LumenFin ---
    after_errors: list[str] = []
    for spec in BASELINE_CASES:
        if not spec.get("rerun_live"):
            continue
        docs = list(spec["docs"])
        if docs and not Path(docs[0]).exists():
            print("FAIL missing doc", docs[0])
            after_errors.append(f"missing doc {docs[0]}")
            continue
        try:
            state = _live_analyze(spec["query"], docs, f"baseline-{spec['id']}")
        except Exception as exc:  # noqa: BLE001
            msg = f"{spec['id']}: live analyze failed: {exc}"
            print("FAIL", msg)
            after_errors.append(msg)
            continue
        state_out = OUT / "states" / f"after_{spec['id']}_state.json"
        _dump(state_out, state)
        run = _export(state)
        run["run_id"] = f"after-{spec['id']}"
        _dump(FINRUN / "after" / f"{spec['id']}.json", run)
        case = _load(spec["case"])
        ev = _evaluate(run, case, OUT / "eval" / "after" / spec["id"])
        ev.update(
            {
                "id": spec["id"],
                "label": spec["label"],
                "cohort": "after",
                "state_path": str(state_out),
                "exporter": "lumenfin.finrun.export_finrun_state",
            }
        )
        results.append(ev)
        print(
            f"[after] {spec['id']}: score={ev['score']} checkable={ev['checkable_count']} "
            f"entities={ev['entities']} llm={ev['llm_backend']} status={ev['workflow_status']}"
        )

    env_info["after_errors"] = after_errors
    env_info["finished_at"] = _now()
    _dump(OUT / "results.json", {"env": env_info, "results": results, "generated_at": _now()})
    _write_report(env_info, results)
    print(f"Wrote {REPORT}")
    if after_errors:
        print("AFTER_ERRORS", after_errors)
        return 1
    return 0


def _write_report(env: dict[str, Any], results: list[dict[str, Any]]) -> None:
    before = [r for r in results if r.get("cohort") == "before"]
    after = [r for r in results if r.get("cohort") == "after"]
    after_failures = _collect_failures(after)
    before_failures = _collect_failures(before)

    def mean_score(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return round(sum(float(r["score"]) for r in rows) / len(rows), 2)

    def bucket(failures: list[dict[str, Any]]) -> dict[str, list[str]]:
        p0, p1, p2 = [], [], []
        seen = set()
        for f in failures:
            key = (f.get("metric"), f.get("message"))
            if key in seen:
                continue
            seen.add(key)
            line = f"`{f.get('case')}` / {f.get('metric')}: {f.get('message')}"
            sev = str(f.get("severity") or "")
            if sev in {"critical", "high"} or f.get("metric") in {
                "entity_leakage",
                "numeric_correctness",
                "runtime_llm",
                "financial_fact_coverage",
            }:
                if "fallback" in str(f.get("message")).lower() or f.get("metric") == "runtime_llm":
                    p0.append(line)
                elif f.get("metric") in {"entity_leakage", "numeric_correctness", "financial_fact_coverage", "runtime_workflow"}:
                    p0.append(line)
                else:
                    p1.append(line)
            elif sev == "medium":
                p1.append(line)
            else:
                p2.append(line)
        return {"P0": p0, "P1": p1, "P2": p2}

    after_buckets = bucket(after_failures)

    lines: list[str] = []
    lines.append("# LumenFin Final Reliability Baseline")
    lines.append("")
    lines.append(f"Generated: {_now()}")
    lines.append("")
    lines.append("Evaluation uses **corrected FinAgentBench** with canonical FinRun only:")
    lines.append("`LumenFin state → export_finrun_state() → FinAgentBench evaluate` (profile=`ci`).")
    lines.append("No mock LLM. After cohort is a **fresh live API** re-run. Before cohort is the prior live E2E audit states.")
    lines.append("Benchmark thresholds were not modified for this report.")
    lines.append("")
    lines.append("## Environment")
    lines.append("")
    lines.append("| Key | Value |")
    lines.append("|-----|-------|")
    for k, v in env.items():
        lines.append(f"| {k} | `{v}` |")
    lines.append("")
    lines.append("## 1. Current Score")
    lines.append("")
    lines.append(f"| Cohort | Mean FinAgentBench score (3 core cases) |")
    lines.append(f"|--------|----------------------------------------:|")
    lines.append(f"| Before (pre P0/P1 audit states) | {mean_score(before)} |")
    lines.append(f"| After (fresh live + P0/P1 code) | {mean_score(after)} |")
    lines.append("")
    lines.append("### Per-case")
    lines.append("")
    lines.append(
        "| Case | Before score | After score | Before entities | After entities | "
        "Before checkable | After checkable | Before status/llm | After status/llm |"
    )
    lines.append("|------|-------------:|------------:|-----------------|----------------|-----------------:|----------------:|-------------------|------------------|")
    ids = ["apple_live", "nvidia_10k", "tesla_live"]
    bmap = {r["id"]: r for r in before}
    amap = {r["id"]: r for r in after}
    for cid in ids:
        b = bmap.get(cid) or {}
        a = amap.get(cid) or {}
        lines.append(
            f"| {b.get('label') or a.get('label') or cid} | {b.get('score')} | {a.get('score')} | "
            f"`{b.get('entities')}` | `{a.get('entities')}` | {b.get('checkable_count')} | {a.get('checkable_count')} | "
            f"{b.get('workflow_status')}/{b.get('llm_backend')} | {a.get('workflow_status')}/{a.get('llm_backend')} |"
        )
    lines.append("")
    lines.append("### Metric focus (After)")
    lines.append("")
    lines.append("| Case | numeric_correctness | entity_leakage | evidence_coverage | retrieval_provenance | risk_disclosure |")
    lines.append("|------|--------------------:|---------------:|------------------:|---------------------:|----------------:|")
    for cid in ids:
        a = amap.get(cid) or {}
        d = a.get("metric_detail") or {}
        def sc(name: str) -> Any:
            return (d.get(name) or {}).get("score")
        lines.append(
            f"| {a.get('label') or cid} | {sc('numeric_correctness')} | {sc('entity_leakage')} | "
            f"{sc('evidence_coverage')} | {sc('retrieval_provenance')} | {sc('risk_disclosure')} |"
        )
    lines.append("")
    lines.append("## 2. Top Failures (After — severity ordered)")
    lines.append("")
    lines.append("### P0")
    lines.append("")
    for item in after_buckets["P0"][:20] or ["- None classified P0"]:
        lines.append(f"- {item}" if not item.startswith("-") else item)
    lines.append("")
    lines.append("### P1")
    lines.append("")
    for item in after_buckets["P1"][:20] or ["- None classified P1"]:
        lines.append(f"- {item}" if not item.startswith("-") else item)
    lines.append("")
    lines.append("### P2")
    lines.append("")
    for item in after_buckets["P2"][:15] or ["- None classified P2"]:
        lines.append(f"- {item}" if not item.startswith("-") else item)
    lines.append("")
    lines.append("## 3. Before / After Comparison")
    lines.append("")
    lines.append("| Dimension | Before | After | Read |")
    lines.append("|-----------|--------|-------|------|")
    # Entity leakage
    b_nvda = bmap.get("nvidia_10k") or {}
    a_nvda = amap.get("nvidia_10k") or {}
    b_leak = any(
        f.get("metric") == "entity_leakage"
        for f in before_failures
        if f.get("case") == "nvidia_10k"
    ) or (len(b_nvda.get("entities") or []) > 2)
    a_leak = any(
        f.get("metric") == "entity_leakage"
        for f in after_failures
        if f.get("case") == "nvidia_10k"
    ) or (len(a_nvda.get("entities") or []) > 2)
    lines.append(
        f"| Entity routing (NVDA 10-K) | entities=`{b_nvda.get('entities')}` leak={b_leak} | "
        f"entities=`{a_nvda.get('entities')}` leak={a_leak} | "
        f"{'Improved issuer isolation' if b_leak and not a_leak else 'Check'} |"
    )
    lines.append(
        f"| Numeric checkable (mean) | "
        f"{round(sum(r.get('checkable_count') or 0 for r in before)/max(1,len(before)),1)} | "
        f"{round(sum(r.get('checkable_count') or 0 for r in after)/max(1,len(after)),1)} | "
        f"Formula verification path active when metrics exist |"
    )
    lines.append(
        f"| Mean bench score | {mean_score(before)} | {mean_score(after)} | "
        f"Informational only — optimize by failure type |"
    )
    lines.append(
        f"| DeepSeek primary | "
        f"{sum(1 for r in before if str(r.get('llm_backend'))=='deepseek')}/{len(before)} | "
        f"{sum(1 for r in after if str(r.get('llm_backend'))=='deepseek')}/{len(after)} | "
        f"Fallback remains a baseline risk if present |"
    )
    lines.append("")
    lines.append("### Known issues — detection status (After)")
    lines.append("")
    lines.append("| Known issue | Detected by corrected bench? | Evidence |")
    lines.append("|-------------|------------------------------|----------|")
    fact_gap = any(f.get("metric") in {"financial_fact_coverage", "numeric_correctness"} for f in after_failures)
    lines.append(
        f"| Financial fact coverage | {'YES' if fact_gap or any((r.get('checkable_count') or 0)==0 for r in after) else 'PARTIAL'} | "
        f"checkable counts / numeric findings |"
    )
    cite_gap = any("citation" in str(f.get("metric")) or "#p" in str(f.get("message")) for f in after_failures) or any(
        (r.get("citation_markers") or 0) == 0 and r.get("id") == "nvidia_10k" for r in after
    )
    lines.append(f"| Claim → evidence binding | {'YES/PARTIAL' if cite_gap else 'WEAK'} | #pN markers + evidence_coverage |")
    fb = any(f.get("metric") == "runtime_llm" for f in after_failures)
    lines.append(f"| DeepSeek fallback | {'YES' if fb else 'NO on this After cohort'} | `metadata.llm_backend` |")
    lines.append("")
    lines.append("## 4. Optimization Roadmap (by failure type — not by score)")
    lines.append("")
    lines.append("### P0 — do next")
    lines.append("")
    lines.append("1. **Issuer-only SEC fill when upload lacks AST metrics** — so NVDA 10-K completes quant without reintroducing peer fan-out.")
    lines.append("2. **Stabilize DeepSeek primary path** — eliminate local-fallback on production baselines; treat fallback as hard fail in CI gate.")
    lines.append("3. **Financial fact coverage for live issuers** — ensure every completed Apple/Tesla/NVIDIA run exports formula+inputs (already works when quant completes).")
    lines.append("")
    lines.append("### P1")
    lines.append("")
    lines.append("1. **Claim → citation binding** — require `#pN` (or evidence ids) on material numeric/risk claims for PDF-backed runs.")
    lines.append("2. **Evidence consistency for segment vs consolidated** — export statement `scope` into FinRun facts when available.")
    lines.append("3. **Heading-complete report contract** — ensure Risk/Compliance/Disclaimer remain true headings under fail-loud paths.")
    lines.append("")
    lines.append("### P2")
    lines.append("")
    lines.append("1. Expand issuer case pack (MSFT/AMD) with forbidden_entities.")
    lines.append("2. Gold numeric set (FY totals) separate from AST ratio checks.")
    lines.append("3. Keep FinAgentBench mutations in CI (must stay 4/4).")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Results: `{OUT / 'results.json'}`")
    lines.append(f"- FinRuns: `{FINRUN}`")
    lines.append(f"- Fresh After states: `{OUT / 'states'}`")
    lines.append("")

    text = "\n".join(lines)
    REPORT.write_text(text, encoding="utf-8")
    REPORT_FAB.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
