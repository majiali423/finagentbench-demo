from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finagentbench.benchmark import run_benchmark_suite


class MutationSuiteTestCase(unittest.TestCase):
    def test_all_reliability_mutations_are_detected(self) -> None:
        report = run_benchmark_suite(ROOT / "benchmarks" / "mutations" / "suite.json")

        self.assertTrue(report["passed"])
        self.assertEqual(report["false_positives"], 0)
        self.assertEqual(report["detection_rate"], 1.0)
        detected = {
            item["failure_type"]
            for item in report["items"]
            if item["failure_type"] != "none"
            and not item["actual_passed"]
            and not item["missing_expected_findings"]
        }
        self.assertEqual(detected, {
            "wrong_number", "wrong_entity", "missing_citation", "missing_risk",
            "missing_metric_period_provenance", "query_period_source",
            "assumed_period_alignment", "missing_source_record",
            "formula_cross_period_inputs", "missing_period_alignment",
            "metric_period_drift",
        })
        multi = next(item for item in report["items"] if item["id"] == "period_multi_rag_baseline")
        self.assertTrue(multi["actual_passed"])

    def test_offline_demo_emits_baseline_and_mutation_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_offline_demo.py"),
                    "--out-dir",
                    tmp,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((Path(tmp) / "mutation_detection_report.json").exists())
            reports = list((Path(tmp) / "baseline").glob("*_eval_report.json"))
            self.assertEqual(len(reports), 1)


if __name__ == "__main__":
    unittest.main()
