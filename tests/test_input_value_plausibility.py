"""Case-driven input_value_plausibility bounds."""
from __future__ import annotations

import math
import unittest

from finagentbench.metrics.input_value_plausibility import input_value_plausibility
from finagentbench.provenance import case_hash
from finagentbench.schema import validate_case


def _run(value: float, *, unit: str = "billion_usd", name: str = "revenue") -> dict:
    return {
        "run_id": "bounds",
        "entities": ["Microsoft"],
        "steps": [],
        "metrics": [
            {
                "entity": "Microsoft",
                "name": "x",
                "value": 1,
                "inputs": {name: {"value": value, "unit": unit, "currency": "USD"}},
            }
        ],
        "evidence": [],
        "market_data": [],
        "final_output": "ok",
    }


class InputValuePlausibilityTestCase(unittest.TestCase):
    def test_max_inclusive_and_over(self) -> None:
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        self.assertTrue(input_value_plausibility(_run(1000), case).passed)
        self.assertFalse(input_value_plausibility(_run(1000.1), case).passed)

    def test_min_inclusive_and_under(self) -> None:
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {
                "operating_income": {"unit": "billion_usd", "min": -500, "max": 500}
            },
        }
        self.assertTrue(input_value_plausibility(_run(-500, name="operating_income"), case).passed)
        self.assertFalse(input_value_plausibility(_run(-5000, name="operating_income"), case).passed)

    def test_no_bounds_skips(self) -> None:
        self.assertTrue(
            input_value_plausibility(
                _run(5000), {"enabled_metrics": ["input_value_plausibility"]}
            ).passed
        )

    def test_unit_mismatch_skips_bound(self) -> None:
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        self.assertTrue(input_value_plausibility(_run(5000, unit="million"), case).passed)

    def test_nan_and_inf_fail(self) -> None:
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        self.assertFalse(input_value_plausibility(_run(math.nan), case).passed)
        self.assertFalse(input_value_plausibility(_run(math.inf), case).passed)

    def test_string_numeric_parsed(self) -> None:
        run = _run(100)
        run["metrics"][0]["inputs"]["revenue"]["value"] = "250.5"
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        self.assertTrue(input_value_plausibility(run, case).passed)

    def test_case_hash_and_validation(self) -> None:
        base = {
            "id": "b",
            "scoring_version": "2",
            "expected_entities": [],
            "required_steps": [],
        }
        with_bounds = {
            **base,
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
            "entity_aliases": {"Microsoft": ["MSFT"]},
            "peer_section_aliases": ["Peer Comparison"],
        }
        validate_case(base)
        validate_case(with_bounds)
        self.assertNotEqual(case_hash(base), case_hash(with_bounds))
        with self.assertRaises(Exception):
            validate_case(
                {
                    **base,
                    "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 10, "max": 1}},
                }
            )

    def test_none_value_score_pass_consistent(self) -> None:
        run = _run(100)
        run["metrics"][0]["inputs"]["revenue"]["value"] = None
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        result = input_value_plausibility(run, case)
        if result.findings:
            self.assertFalse(result.passed)
        else:
            # No checkable values → empty contract (100/True), never score=0 with passed=True.
            self.assertEqual(result.score, 100.0)
            self.assertTrue(result.passed)

    def test_mixed_none_and_valid_scores_only_valid(self) -> None:
        run = {
            "run_id": "mixed",
            "entities": ["Microsoft"],
            "steps": [],
            "metrics": [
                {
                    "entity": "Microsoft",
                    "name": "x",
                    "value": 1,
                    "inputs": {
                        "revenue": {"value": 250.0, "unit": "billion_usd", "currency": "USD"},
                        "operating_income": {"value": None, "unit": "billion_usd", "currency": "USD"},
                    },
                }
            ],
            "evidence": [],
            "market_data": [],
            "final_output": "ok",
        }
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {
                "revenue": {"unit": "billion_usd", "min": 0, "max": 1000},
                "operating_income": {"unit": "billion_usd", "min": -500, "max": 500},
            },
        }
        result = input_value_plausibility(run, case)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 100.0)

    def test_bounds_reject_nan_and_inf(self) -> None:
        base = {
            "id": "b",
            "scoring_version": "2",
            "expected_entities": [],
            "required_steps": [],
        }
        for bad in (math.nan, math.inf, -math.inf, "nan", "inf"):
            with self.subTest(bad=bad):
                with self.assertRaises(Exception):
                    validate_case(
                        {
                            **base,
                            "input_value_bounds": {
                                "revenue": {"unit": "billion_usd", "min": 0, "max": bad}
                            },
                        }
                    )


if __name__ == "__main__":
    unittest.main()
