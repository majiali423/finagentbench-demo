#!/usr/bin/env python3
"""Key-free FinAgentBench demo: one passing run and four detected mutations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finagentbench.adapters import load_run_file
from finagentbench.benchmark import run_benchmark_suite
from finagentbench.profiles import apply_profile
from finagentbench.provenance import attach_provenance
from finagentbench.report import write_eval_report
from finagentbench.runner import evaluate_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs" / "offline_demo",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    run_path = ROOT / "fixtures" / "pass_due_diligence_finrun.json"
    case_path = ROOT / "fixtures" / "case_due_diligence.json"
    run = load_run_file(run_path, "generic")
    case = apply_profile(json.loads(case_path.read_text(encoding="utf-8")), "ci")
    baseline = attach_provenance(
        evaluate_run(run, case),
        case,
        profile="ci",
        adapter="generic",
    )
    baseline_paths = write_eval_report(baseline, args.out_dir / "baseline")

    mutations = run_benchmark_suite(ROOT / "benchmarks" / "mutations" / "suite.json")
    mutation_path = args.out_dir / "mutation_detection_report.json"
    mutation_path.write_text(json.dumps(mutations, indent=2), encoding="utf-8")

    rows = []
    for item in mutations["items"]:
        if item["failure_type"] == "none":
            continue
        detected = not item["actual_passed"] and not item["missing_expected_findings"]
        rows.append((item["failure_type"], detected, item["actual_findings"]))

    print(f"baseline: {'PASS' if baseline.passed else 'FAIL'} score={baseline.score}")
    for failure_type, detected, findings in rows:
        print(
            f"{failure_type}: {'DETECTED' if detected else 'MISSED'} "
            f"findings={','.join(findings)}"
        )
    print(f"baseline report: {baseline_paths['json']}")
    print(f"mutation report: {mutation_path}")
    return 0 if baseline.passed and mutations["passed"] and all(row[1] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
