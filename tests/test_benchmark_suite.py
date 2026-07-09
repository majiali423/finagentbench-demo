from __future__ import annotations

import unittest
from pathlib import Path

from finagentbench.benchmark import run_benchmark_suite, run_semantic_benchmark_suite


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkSuiteTestCase(unittest.TestCase):
    def test_due_diligence_suite_detects_curated_failures(self) -> None:
        payload = run_benchmark_suite(ROOT / "benchmarks" / "due_diligence" / "suite.json")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total_traces"], 10)
        self.assertEqual(payload["expected_failures"], 9)
        self.assertEqual(payload["detected_failures"], 9)
        self.assertEqual(payload["detection_rate"], 1.0)
        self.assertGreaterEqual(payload["covered_failure_type_count"], 8)

    def test_semantic_golden_suite_matches_human_labels(self) -> None:
        payload = run_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "evidence_support_golden.json"
        )
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total"], 20)
        self.assertEqual(payload["matched"], 20)
        self.assertEqual(payload["accuracy"], 1.0)
        self.assertEqual(payload["false_positives"], 0)
        self.assertEqual(payload["false_negatives"], 0)
        self.assertGreaterEqual(len(payload["by_failure_type"]), 10)


if __name__ == "__main__":
    unittest.main()
