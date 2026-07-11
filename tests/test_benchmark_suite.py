from __future__ import annotations

import unittest
from pathlib import Path

from finagentbench.benchmark import (
    run_benchmark_suite,
    run_live_semantic_benchmark_suite,
    run_semantic_benchmark_suite,
)


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
        self.assertEqual(payload["benchmark_mode"], "static_judge_replay")
        self.assertEqual(payload["measures"], "pipeline_replay_consistency_not_live_llm_accuracy")
        self.assertEqual(payload["replay_match_rate"], 1.0)
        self.assertEqual(payload["false_positives"], 0)
        self.assertEqual(payload["false_negatives"], 0)
        self.assertGreaterEqual(len(payload["by_failure_type"]), 10)

    def test_lumenfin_regression_suite_catches_before_after_failures(self) -> None:
        payload = run_benchmark_suite(ROOT / "benchmarks" / "lumenfin_regression" / "suite.json")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total_traces"], 3)
        self.assertEqual(payload["expected_failures"], 2)
        self.assertEqual(payload["detected_failures"], 2)
        items = {item["id"]: item for item in payload["items"]}
        self.assertTrue(items["lumenfin_baseline"]["actual_passed"])
        self.assertIn("numeric_correctness", items["lumenfin_wrong_quant"]["actual_findings"])
        self.assertIn("risk_disclosure", items["lumenfin_missing_risk_section"]["actual_findings"])

    def test_live_semantic_benchmark_reports_judge_alignment(self) -> None:
        payload = run_live_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "evidence_support_golden.json",
            {
                "provider": "static",
                "results": {
                    "evidence_support": {
                        "score": 91,
                        "passed": True,
                        "rationale": "The claim is supported.",
                        "severity": "low",
                        "labels": ["supported"],
                    }
                },
            },
            limit=1,
        )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["benchmark_mode"], "live_llm_judge_small_sample")
        self.assertEqual(
            payload["measures"],
            "live_judge_alignment_with_human_labels_not_production_accuracy",
        )
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["matched"], 1)
        self.assertEqual(payload["items"][0]["judge"]["provider"], "static")


if __name__ == "__main__":
    unittest.main()
