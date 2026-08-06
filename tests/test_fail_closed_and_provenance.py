from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.metrics.evidence_consistency import evidence_consistency
from finagentbench.metrics.evidence import evidence_coverage
from finagentbench.metrics.numeric import numeric_correctness
from finagentbench.metrics.temporal import temporal_consistency
from finagentbench.metrics.unit_currency import unit_currency_consistency
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

    def test_evidence_coverage_empty_trace_fails_when_require_checkable(self) -> None:
        result = evidence_coverage(
            _empty_run(),
            {
                "expected_entities": ["NVIDIA"],
                "require_checkable_metrics": True,
            },
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_unit_currency_empty_trace_fails_when_require_checkable(self) -> None:
        result = unit_currency_consistency(
            _empty_run(),
            {
                "enabled_metrics": ["unit_currency_consistency"],
                "require_checkable_metrics": True,
            },
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_unit_currency_detects_absurd_billion_magnitude(self) -> None:
        # Magnitude checks moved to input_value_plausibility Case bounds.
        from finagentbench.metrics.input_value_plausibility import input_value_plausibility

        run = {
            "run_id": "absurd-unit",
            "entities": ["Microsoft"],
            "steps": [],
            "metrics": [
                {
                    "entity": "Microsoft",
                    "name": "operating_margin",
                    "value": 0.45,
                    "formula": "operating_income / revenue",
                    "inputs": {
                        "operating_income": {
                            "value": 109433.0,
                            "unit": "billion_usd",
                            "currency": "USD",
                            "period": "FY2024",
                        },
                        "revenue": {
                            "value": 245122.0,
                            "unit": "billion_usd",
                            "currency": "USD",
                            "period": "FY2024",
                        },
                    },
                }
            ],
            "evidence": [],
            "final_output": "Microsoft analysis.",
        }
        unit_result = unit_currency_consistency(
            run,
            {
                "enabled_metrics": ["unit_currency_consistency"],
                "require_unit_currency_consistency": True,
            },
        )
        self.assertTrue(unit_result.passed)
        result = input_value_plausibility(
            run,
            {
                "enabled_metrics": ["input_value_plausibility"],
                "input_value_bounds": {
                    "revenue": {"unit": "billion_usd", "min": 0, "max": 1000},
                    "operating_income": {"unit": "billion_usd", "min": -500, "max": 500},
                },
            },
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("outside case-configured bounds" in f.message for f in result.findings))

    def test_temporal_empty_trace_fails_when_require_checkable(self) -> None:
        result = temporal_consistency(
            _empty_run(),
            {
                "require_temporal_consistency": True,
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
        self.assertEqual(report.scoring_version, "1")
        self.assertEqual(report.enabled_metrics, ["entity_coverage"])
        self.assertEqual(report.case_hash, case_hash(case))
        self.assertTrue(report.tool_version)
        self.assertEqual(report.case_mode, "quality")
        self.assertFalse(report.derived_expectations)


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
