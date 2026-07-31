"""Run the two PDF RC cases that previously had unit-scale bugs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FAB = Path(__file__).resolve().parents[1]
SCRIPTS = FAB / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from repo_paths import finagentbench_root, lumenfin_root  # noqa: E402

lumen = lumenfin_root()
fab = finagentbench_root()
lumen_src = str(lumen / "src")
if lumen_src not in sys.path:
    sys.path.insert(0, lumen_src)

from run_rc_validation import _rc_cases, _run_live_case  # noqa: E402
import rc_runtime as runtime  # noqa: E402


def main() -> int:
    out = fab / "outputs" / "lumenfin_rc_pdf_verify"
    out.mkdir(parents=True, exist_ok=True)

    print("=== LIVE PREFLIGHT ===", flush=True)
    preflight = runtime.live_preflight(lumen_root=lumen)
    fingerprint = preflight["fingerprint"]
    print(f"fingerprint provider={fingerprint.get('provider')} model={fingerprint.get('model')}", flush=True)

    wanted = {"rc_nvidia_10k", "rc_msft_long"}
    cases = [c for c in _rc_cases(lumen, fab) if c["id"] in wanted]
    if len(cases) != 2:
        print(f"expected 2 cases, got {[c['id'] for c in cases]}", flush=True)
        return 2

    rows = []
    for spec in cases:
        print(f"\n=== LIVE {spec['id']} ===", flush=True)
        row = _run_live_case(
            lumen=lumen,
            out=out,
            spec=spec,
            expected_fingerprint=fingerprint,
        )
        rows.append(row)
        fab_score = None
        if isinstance(row.get("fab"), dict):
            fab_score = row["fab"].get("score")
        print(
            f"[{spec['id']}] status={row.get('workflow_status')} ok={row.get('judgment', {}).get('ok')} "
            f"fab={fab_score} elapsed_ms={row.get('elapsed_ms')}",
            flush=True,
        )

        reports = sorted(
            (out / "states").glob(f"rc-{spec['id']}-*_report.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        state_path = out / "states" / f"{spec['id']}_state.json"
        if reports:
            text = reports[0].read_text(encoding="utf-8")
            has_risk = bool(re.search(r"(?m)^##\s+(\d+\.\s+)?Risk\b", text))
            absurd = re.findall(r"\d{4,}\.\d+\s*billion\s*USD", text)
            print(f"  report={reports[0].name}", flush=True)
            print(f"  has_##_Risk={has_risk}", flush=True)
            print(f"  absurd_billion_phrases={absurd[:5]}", flush=True)
        if state_path.exists():
            st = json.loads(state_path.read_text(encoding="utf-8"))
            claims = st.get("claims") or []
            abs_claims = [
                c
                for c in claims
                if isinstance(c, dict)
                and c.get("metric_name") in {"revenue", "operating_income", "r_and_d", "ebitda"}
            ]
            for c in abs_claims:
                print(
                    f"  claim {c.get('metric_name')}: value={c.get('value')} unit={c.get('unit')} "
                    f"verification={c.get('verification')} | {c.get('statement')}",
                    flush=True,
                )

        evals = sorted(
            (out / "eval" / spec["id"]).glob("*_eval_report.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if evals:
            data = json.loads(evals[0].read_text(encoding="utf-8"))
            metrics = (
                {m["name"]: m for m in data.get("metrics", [])}
                if isinstance(data.get("metrics"), list)
                else {}
            )
            for name in ("section_presence", "unit_currency_consistency", "numeric_correctness"):
                m = metrics.get(name) or {}
                print(f"  fab.{name}={m.get('score')} findings={m.get('findings')}", flush=True)

    summary = {
        "rows": [
            {
                "id": r.get("id"),
                "status": r.get("workflow_status"),
                "ok": (r.get("judgment") or {}).get("ok"),
                "fab": (r.get("fab") or {}).get("score") if isinstance(r.get("fab"), dict) else r.get("fab"),
            }
            for r in rows
        ]
    }
    (out / "verify_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    all_ok = all(bool(x["ok"]) for x in summary["rows"])
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
