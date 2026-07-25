#!/usr/bin/env python3
"""Run the deterministic four-mutation reliability gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finagentbench.benchmark import run_benchmark_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        type=Path,
        default=ROOT / "benchmarks" / "mutations" / "suite.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "mutation_detection_report.json",
    )
    args = parser.parse_args()

    report = run_benchmark_suite(args.suite)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path = args.out.with_suffix(".md")
    _write_markdown(report, markdown_path)

    print(f"Wrote {args.out}")
    print(f"Wrote {markdown_path}")
    return 0 if report["passed"] and _all_four_detected(report) else 1


def _all_four_detected(report: dict) -> bool:
    expected = {"wrong_number", "wrong_entity", "missing_citation", "missing_risk"}
    detected = {
        item["failure_type"]
        for item in report["items"]
        if item["failure_type"] in expected
        and not item["actual_passed"]
        and not item["missing_expected_findings"]
    }
    return detected == expected


def _write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Mutation Detection Report",
        "",
        f"- Suite: `{report['suite_id']}`",
        f"- Detection rate: `{report['detection_rate']}`",
        f"- Gate: `{'PASS' if report['passed'] and _all_four_detected(report) else 'FAIL'}`",
        "",
        "| Mutation | Detected | Findings |",
        "|----------|:--------:|----------|",
    ]
    for item in report["items"]:
        if item["failure_type"] == "none":
            continue
        detected = not item["actual_passed"] and not item["missing_expected_findings"]
        findings = ", ".join(item["actual_findings"]) or "-"
        lines.append(
            f"| {item['failure_type']} | {'YES' if detected else 'NO'} | {findings} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
