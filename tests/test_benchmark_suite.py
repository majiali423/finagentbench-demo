from __future__ import annotations

import unittest
from pathlib import Path

from finagentbench.benchmark import run_benchmark_suite


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


if __name__ == "__main__":
    unittest.main()
