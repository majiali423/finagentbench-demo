#!/usr/bin/env python3
"""Run the deterministic reliability mutation gate (core + extended)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finagentbench.benchmark import run_benchmark_suite

CORE_MUTATIONS = ("wrong_number", "wrong_entity", "missing_citation", "missing_risk")
EXTENDED_MUTATIONS = (
    "missing_metric_period_provenance",
    "query_period_source",
    "assumed_period_alignment",
    "missing_source_record",
    "formula_cross_period_inputs",
    "missing_period_alignment",
    "metric_period_drift",
)


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
    core_ok = _detected(report, CORE_MUTATIONS)
    extended_ok = _detected(report, EXTENDED_MUTATIONS)
    report["core_mutations_detected"] = f"{sum(core_ok.values())}/{len(CORE_MUTATIONS)}"
    report["extended_mutations_detected"] = (
        f"{sum(extended_ok.values())}/{len(EXTENDED_MUTATIONS)}"
    )
    report["total_negative_controls"] = (
        f"{sum(core_ok.values()) + sum(extended_ok.values())}/"
        f"{len(CORE_MUTATIONS) + len(EXTENDED_MUTATIONS)}"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path = args.out.with_suffix(".md")
    _write_markdown(report, markdown_path, core_ok, extended_ok)

    print(f"Wrote {args.out}")
    print(f"Wrote {markdown_path}")
    print(f"Core reliability mutations: {report['core_mutations_detected']}")
    print(f"Extended provenance/period mutations: {report['extended_mutations_detected']}")
    print(f"Total negative controls: {report['total_negative_controls']}")
    gate_ok = (
        report["passed"]
        and all(core_ok.values())
        and all(extended_ok.values())
    )
    return 0 if gate_ok else 1


def _detected(report: dict, expected: tuple[str, ...]) -> dict[str, bool]:
    found = {
        item["failure_type"]: (
            not item["actual_passed"] and not item["missing_expected_findings"]
        )
        for item in report["items"]
        if item["failure_type"] in expected
    }
    return {name: bool(found.get(name)) for name in expected}


def _write_markdown(
    report: dict,
    path: Path,
    core_ok: dict[str, bool],
    extended_ok: dict[str, bool],
) -> None:
    lines = [
        "# Mutation Detection Report",
        "",
        f"- Suite: `{report['suite_id']}`",
        f"- Detection rate: `{report['detection_rate']}`",
        f"- Core reliability mutations: `{report['core_mutations_detected']}`",
        (
            "- Extended provenance/period mutations: "
            f"`{report['extended_mutations_detected']}`"
        ),
        f"- Total negative controls: `{report['total_negative_controls']}`",
        (
            f"- Gate: `{'PASS' if report['passed'] and all(core_ok.values()) and all(extended_ok.values()) else 'FAIL'}`"
        ),
        "",
        "## Core reliability mutations",
        "",
        "| Mutation | Detected | Findings |",
        "|----------|:--------:|----------|",
    ]
    by_type = {
        item["failure_type"]: item
        for item in report["items"]
        if item["failure_type"] != "none"
    }
    for name in CORE_MUTATIONS:
        item = by_type.get(name, {})
        findings = ", ".join(item.get("actual_findings") or []) or "-"
        lines.append(f"| {name} | {'YES' if core_ok.get(name) else 'NO'} | {findings} |")
    lines.extend(
        [
            "",
            "## Extended provenance/period mutations",
            "",
            "| Mutation | Detected | Findings |",
            "|----------|:--------:|----------|",
        ]
    )
    for name in EXTENDED_MUTATIONS:
        item = by_type.get(name, {})
        findings = ", ".join(item.get("actual_findings") or []) or "-"
        lines.append(
            f"| {name} | {'YES' if extended_ok.get(name) else 'NO'} | {findings} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
