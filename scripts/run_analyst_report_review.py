"""Live analyst-facing report review: Apple, AAPL vs MSFT, MSFT PDF."""
from __future__ import annotations

import json
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
    out = fab / "outputs" / "lumenfin_analyst_review"
    out.mkdir(parents=True, exist_ok=True)

    print("=== LIVE PREFLIGHT ===", flush=True)
    preflight = runtime.live_preflight(lumen_root=lumen)
    fingerprint = preflight["fingerprint"]
    print(
        f"fingerprint provider={fingerprint.get('provider')} model={fingerprint.get('model')}",
        flush=True,
    )

    order = ["rc_apple_live", "rc_compare_aapl_msft", "rc_msft_long"]
    wanted = set(order)
    cases = [c for c in _rc_cases(lumen, fab) if c["id"] in wanted]
    cases = sorted(cases, key=lambda c: order.index(c["id"]))
    if len(cases) != len(order):
        print(f"expected {order}, got {[c['id'] for c in cases]}", flush=True)
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
        fab_score = (row.get("fab") or {}).get("score") if isinstance(row.get("fab"), dict) else None
        print(
            f"[{spec['id']}] status={row.get('workflow_status')} "
            f"ok={(row.get('judgment') or {}).get('ok')} fab={fab_score} "
            f"verified={(row.get('claim_coverage') or {}).get('verified_total')} "
            f"elapsed_ms={row.get('elapsed_ms')}",
            flush=True,
        )
        reports = sorted(
            (out / "states").glob(f"rc-{spec['id']}-*_report.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if reports:
            print(f"  report={reports[0].name}", flush=True)

    summary = [
        {
            "id": r.get("id"),
            "status": r.get("workflow_status"),
            "ok": (r.get("judgment") or {}).get("ok"),
            "fab": (r.get("fab") or {}).get("score") if isinstance(r.get("fab"), dict) else r.get("fab"),
        }
        for r in rows
    ]
    (out / "analyst_review_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("\n=== SUMMARY ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if all(bool(x.get("ok")) for x in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
