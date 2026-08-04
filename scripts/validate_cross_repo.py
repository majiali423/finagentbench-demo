#!/usr/bin/env python3
"""Offline, portable LumenFin → FinRun → FinAgentBench validation entry."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from repo_paths import finagentbench_root, load_lumenfin_export_finrun_state, lumenfin_root

CORE_MUTATIONS = frozenset(
    {"wrong_number", "wrong_entity", "missing_citation", "missing_risk"}
)
EXTENDED_MUTATIONS = frozenset(
    {
        "missing_metric_period_provenance",
        "query_period_source",
        "assumed_period_alignment",
        "missing_source_record",
        "formula_cross_period_inputs",
        "missing_period_alignment",
        "metric_period_drift",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=finagentbench_root() / "outputs" / "cross_repo_validation",
    )
    parser.add_argument("--profile", default="ci", choices=("ci", "audit", "default"))
    args = parser.parse_args()

    fab = finagentbench_root()
    lumen = lumenfin_root()
    _require(lumen / "pyproject.toml", "LumenFin project")
    _require(lumen / "src" / "lumenfin" / "finrun.py", "LumenFin FinRun exporter")
    _require(fab / "fixtures" / "lumenfin_state_sample.json", "sample LumenFin state")
    _require(fab / "fixtures" / "case_lumenfin_diligence.json", "FinAgentBench case")

    export_finrun_state = load_lumenfin_export_finrun_state()
    state = json.loads(
        (fab / "fixtures" / "lumenfin_state_sample.json").read_text(encoding="utf-8")
    )
    finrun = export_finrun_state(state)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    finrun_path = args.out_dir / "sample_finrun.json"
    finrun_path.write_text(json.dumps(finrun, indent=2), encoding="utf-8")

    gate_dir = args.out_dir / "gate"
    gate = subprocess.run(
        [
            sys.executable,
            "-m",
            "finagentbench",
            "gate",
            str(finrun_path),
            "--case",
            str(fab / "fixtures" / "case_lumenfin_diligence.json"),
            "--profile",
            args.profile,
            "--out",
            str(gate_dir),
        ],
        cwd=fab,
        check=False,
    )
    mutation = subprocess.run(
        [
            sys.executable,
            str(fab / "scripts" / "run_mutation_suite.py"),
            "--out",
            str(args.out_dir / "mutation_detection_report.json"),
        ],
        cwd=fab,
        check=False,
    )
    mutation_report_path = args.out_dir / "mutation_detection_report.json"
    mutation_report = (
        json.loads(mutation_report_path.read_text(encoding="utf-8"))
        if mutation_report_path.exists()
        else {}
    )
    mutation_results = {
        item["failure_type"]: (
            not item["actual_passed"] and not item["missing_expected_findings"]
        )
        for item in mutation_report.get("items", [])
        if item.get("failure_type") != "none"
    }
    core_detected = sum(1 for name in CORE_MUTATIONS if mutation_results.get(name))
    extended_detected = sum(1 for name in EXTENDED_MUTATIONS if mutation_results.get(name))
    summary = {
        "lumenfin_root": str(lumen),
        "finagentbench_root": str(fab),
        "lumenfin_commit": _git_revision(lumen),
        "lumenfin_tag": _git_tag_at_head(lumen, "v0.1.0-rc.2"),
        "finagentbench_commit": _git_revision(fab),
        "lumenfin_worktree_dirty": _git_dirty(lumen),
        "finagentbench_worktree_dirty": _git_dirty(fab),
        "finrun_schema_version": finrun.get("schema_version", "legacy-0"),
        "benchmark_profile": args.profile,
        "sample_finrun": str(finrun_path.as_posix().replace(str(fab.as_posix()) + "/", "")),
        "finagentbench_gate_passed": gate.returncode == 0,
        "mutation_gate_passed": mutation.returncode == 0,
        "mutation_detection_rate": mutation_report.get("detection_rate"),
        "core_mutations_detected": f"{core_detected}/{len(CORE_MUTATIONS)}",
        "extended_mutations_detected": f"{extended_detected}/{len(EXTENDED_MUTATIONS)}",
        "total_negative_controls": (
            f"{core_detected + extended_detected}/"
            f"{len(CORE_MUTATIONS) + len(EXTENDED_MUTATIONS)}"
        ),
        "mutation_results": mutation_results,
        "claims_field_present": "claims" in finrun,
        "uses_legacy_revenue_2025_only": _legacy_revenue_only(finrun),
    }
    summary["passed"] = bool(
        summary["finagentbench_gate_passed"] and summary["mutation_gate_passed"]
    )
    summary_path = args.out_dir / "validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


def _legacy_revenue_only(finrun: dict) -> bool:
    """True when market_data relies only on period-suffixed revenue keys."""
    market = finrun.get("market_data") or []
    if not market:
        return False
    saw_legacy = False
    saw_canonical = False
    for row in market:
        if not isinstance(row, dict):
            continue
        if "revenue" in row:
            saw_canonical = True
        if any(str(key).startswith("revenue_") for key in row):
            saw_legacy = True
    return saw_legacy and not saw_canonical


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{label} not found at {path}")


def _git_revision(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unavailable"


def _git_tag_at_head(root: Path, tag: str) -> str:
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "rev-list", "-n", "1", tag],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "unavailable"
    head = _git_revision(root)
    pointed = proc.stdout.strip()
    return tag if pointed and pointed == head else f"{tag}!={pointed}"


def _git_dirty(root: Path) -> bool | str:
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip()) if proc.returncode == 0 else "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
