from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.metrics.registry import available_metrics, resolve_metrics
from finagentbench.runner import evaluate_run
from finagentbench.schema import ValidationError, validate_finrun
from tests.helpers import load_fixture


class SchemaAndRegistryTestCase(unittest.TestCase):
    def test_invalid_finrun_is_rejected_before_scoring(self) -> None:
        with self.assertRaises(ValidationError):
            validate_finrun({"run_id": "bad"})

    def test_case_can_enable_metric_subset(self) -> None:
        case = load_fixture("case_numeric_only.json")
        metrics = resolve_metrics(case)
        self.assertEqual([metric.__name__ for metric in metrics], ["numeric_correctness"])

    def test_numeric_only_case_scores_single_metric(self) -> None:
        report = evaluate_run(load_fixture("pass_finrun.json"), load_fixture("case_numeric_only.json"))
        self.assertEqual(len(report.metrics), 1)
        self.assertEqual(report.metrics[0].name, "numeric_correctness")
        self.assertTrue(report.passed)

    def test_registry_exposes_builtin_metrics(self) -> None:
        names = available_metrics()
        self.assertIn("entity_coverage", names)
        self.assertIn("compliance_language", names)
        self.assertIn("evidence_support", names)
        self.assertIn("risk_quality", names)
        self.assertIn("compliance_semantic", names)

if __name__ == "__main__":
    unittest.main()
