from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.metrics.registry import available_metrics, resolve_metrics
from finagentbench.runner import evaluate_run
from finagentbench.schema import ValidationError, validate_finrun


ROOT = Path(__file__).resolve().parents[1]


class SchemaAndRegistryTestCase(unittest.TestCase):
    def test_invalid_finrun_is_rejected_before_scoring(self) -> None:
        with self.assertRaises(ValidationError):
            validate_finrun({"run_id": "bad"})

    def test_case_can_enable_metric_subset(self) -> None:
        case = _load("case_numeric_only.json")
        metrics = resolve_metrics(case)
        self.assertEqual([metric.__name__ for metric in metrics], ["numeric_correctness"])

    def test_numeric_only_case_scores_single_metric(self) -> None:
        report = evaluate_run(_load("pass_finrun.json"), _load("case_numeric_only.json"))
        self.assertEqual(len(report.metrics), 1)
        self.assertEqual(report.metrics[0].name, "numeric_correctness")
        self.assertTrue(report.passed)

    def test_registry_exposes_builtin_metrics(self) -> None:
        names = available_metrics()
        self.assertIn("entity_coverage", names)
        self.assertIn("compliance_language", names)


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
