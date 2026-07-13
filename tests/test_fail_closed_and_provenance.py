from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.metrics.evidence_consistency import evidence_consistency
from finagentbench.metrics.numeric import numeric_correctness
from finagentbench.provenance import attach_provenance, case_hash
from finagentbench.runner import evaluate_run


class FailClosedAndProvenanceTestCase(unittest.TestCase):
    def test_numeric_empty_trace_fails_when_require_checkable(self) -> None:
        run = _empty_run()
        case = {
            "expected_entities": [],
            "required_steps": [],
            "enabled_metrics": ["numeric_correctness"],
            "require_checkable_metrics": True,
            "min_score": 0,
        }

        report = evaluate_run(run, case)

        metric = report.metrics[0]
        self.assertEqual(metric.name, "numeric_correctness")
        self.assertFalse(metric.passed)
        self.assertEqual(metric.score, 0.0)
        self.assertIn("No checkable items", metric.findings[0].message)

    def test_numeric_empty_trace_still_passes_without_flag(self) -> None:
        result = numeric_correctness(
            _empty_run(),
            {"expected_entities": [], "required_steps": [], "enabled_metrics": ["numeric_correctness"]},
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 100.0)

    def test_evidence_consistency_empty_trace_fails_when_require_checkable(self) -> None:
        result = evidence_consistency(
            _empty_run(),
            {
                "require_evidence_consistency": True,
                "require_checkable_metrics": True,
            },
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_attach_provenance_stamps_case_hash_and_metrics(self) -> None:
        run = {
            "run_id": "prov-demo",
            "entities": [{"name": "A"}],
            "steps": [],
            "metrics": [],
            "evidence": [],
            "market_data": [],
            "final_output": "Research output only and not investment advice.",
        }
        case = {
            "id": "prov_case",
            "expected_entities": ["A"],
            "required_steps": [],
            "enabled_metrics": ["entity_coverage"],
            "min_score": 0,
        }
        report = attach_provenance(evaluate_run(run, case), case, profile="ci", adapter="generic-json")

        self.assertEqual(report.case_id, "prov_case")
        self.assertEqual(report.profile, "ci")
        self.assertEqual(report.adapter, "generic-json")
        self.assertEqual(report.enabled_metrics, ["entity_coverage"])
        self.assertEqual(report.case_hash, case_hash(case))
        self.assertTrue(report.tool_version)


def _empty_run() -> dict:
    return {
        "run_id": "empty-trace",
        "entities": [],
        "steps": [],
        "metrics": [],
        "evidence": [],
        "market_data": [],
        "final_output": "Research output only and not investment advice.",
    }


if __name__ == "__main__":
    unittest.main()
