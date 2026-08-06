from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import _score_results, compare_runs, evaluate_run
from finagentbench.schema import MetricResult, ValidationError, validate_case, validate_finrun
from tests.helpers import load_fixture


def _base_case(**overrides):
    case = {
        "expected_entities": ["A"],
        "required_steps": ["retrieval"],
        "case_mode": "quality",
        "enabled_metrics": ["entity_coverage"],
        "min_score": 50,
    }
    case.update(overrides)
    return case


def _base_run(**overrides):
    run = {
        "run_id": "nested-demo",
        "schema_version": "1.0",
        "entities": [{"name": "A"}],
        "steps": [{"name": "retrieval", "status": "ok"}],
        "metrics": [
            {
                "entity": "A",
                "name": "r_and_d_intensity",
                "value": 0.1,
                "formula": "r_and_d / revenue",
                "inputs": {"r_and_d": 1.0, "revenue": 10.0},
            }
        ],
        "evidence": [{"entity": "A", "citation": "a.pdf#1", "text": "ok"}],
        "market_data": [{"entity": "A", "status": "ok", "provider": "demo"}],
        "final_output": "Research output only and not investment advice.",
    }
    run.update(overrides)
    return run


class CaseValidationHardeningTestCase(unittest.TestCase):
    def test_rejects_nan_inf_min_score_and_tolerances(self) -> None:
        for field, value, pattern in (
            ("min_score", float("nan"), "min_score"),
            ("min_score", float("inf"), "min_score"),
            ("min_score", -float("inf"), "min_score"),
            ("min_score", -1, "between 0 and 100"),
            ("min_score", 101, "between 0 and 100"),
            ("numeric_tolerance", -0.1, "numeric_tolerance"),
            ("numeric_tolerance", float("nan"), "numeric_tolerance"),
            ("evidence_numeric_tolerance", float("inf"), "evidence_numeric_tolerance"),
            ("regression_tolerance", -1, "regression_tolerance"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValidationError, pattern):
                    validate_case(_base_case(**{field: value}))

    def test_rejects_negative_and_non_finite_weights_and_penalties(self) -> None:
        with self.assertRaisesRegex(ValidationError, "metric_weights.entity_coverage"):
            validate_case(_base_case(metric_weights={"entity_coverage": -1}))
        with self.assertRaisesRegex(ValidationError, "metric_weights.entity_coverage"):
            validate_case(_base_case(metric_weights={"entity_coverage": float("nan")}))
        with self.assertRaisesRegex(ValidationError, "metric_weights.entity_coverage"):
            validate_case(_base_case(metric_weights={"entity_coverage": float("inf")}))
        with self.assertRaisesRegex(ValidationError, "unknown metric"):
            validate_case(_base_case(metric_weights={"not_a_metric": 1}))
        with self.assertRaisesRegex(ValidationError, "severity_penalties.high"):
            validate_case(_base_case(severity_penalties={"high": -5}))
        with self.assertRaisesRegex(ValidationError, "severity_penalties.high"):
            validate_case(_base_case(severity_penalties={"high": float("nan")}))
        with self.assertRaisesRegex(ValidationError, "unsupported severity"):
            validate_case(_base_case(severity_penalties={"ultra": 1}))

    def test_rejects_unknown_duplicate_empty_enabled_metrics_and_severities(self) -> None:
        with self.assertRaisesRegex(ValidationError, "unknown metric"):
            validate_case(_base_case(enabled_metrics=["nope"]))
        with self.assertRaisesRegex(ValidationError, "duplicate metric"):
            validate_case(_base_case(enabled_metrics=["entity_coverage", "entity_coverage"]))
        with self.assertRaisesRegex(ValidationError, "non-empty string"):
            validate_case(_base_case(enabled_metrics=[""]))
        with self.assertRaisesRegex(ValidationError, "unknown severity"):
            validate_case(_base_case(block_on_severity=["nuclear"]))
        with self.assertRaisesRegex(ValidationError, "duplicate severity"):
            validate_case(_base_case(block_on_severity=["high", "high"]))

    def test_rejects_empty_entities_steps_and_invalid_sections(self) -> None:
        with self.assertRaisesRegex(ValidationError, "expected_entities"):
            validate_case(_base_case(expected_entities=[""]))
        with self.assertRaisesRegex(ValidationError, "required_steps"):
            validate_case(_base_case(required_steps=[""]))
        with self.assertRaisesRegex(ValidationError, "required_sections"):
            validate_case(_base_case(required_sections=[123]))

    def test_allows_boundary_legal_values(self) -> None:
        validate_case(
            _base_case(
                min_score=0,
                metric_weights={"entity_coverage": 0},
                severity_penalties={"high": 0},
            )
        )
        validate_case(_base_case(min_score=100, metric_weights={"entity_coverage": 1.5}))

    def test_rejects_python_bool_as_numeric(self) -> None:
        with self.assertRaisesRegex(ValidationError, "min_score"):
            validate_case(_base_case(min_score=True))
        with self.assertRaisesRegex(ValidationError, "metric_weights.entity_coverage"):
            validate_case(_base_case(metric_weights={"entity_coverage": True}))
        with self.assertRaisesRegex(ValidationError, "metrics\\[0\\]\\.value"):
            validate_finrun(
                _base_run(
                    metrics=[
                        {
                            "entity": "A",
                            "name": "x",
                            "value": False,
                            "inputs": {"a": 1.0},
                        }
                    ]
                )
            )
        with self.assertRaisesRegex(ValidationError, "inputs\\.a\\.value"):
            validate_finrun(
                _base_run(
                    metrics=[
                        {
                            "entity": "A",
                            "name": "x",
                            "value": 1.0,
                            "inputs": {"a": {"value": True}},
                        }
                    ]
                )
            )

    def test_default_case_mode_is_quality(self) -> None:
        case = {
            "expected_entities": ["A"],
            "required_steps": [],
            "derive_entities_from_run": True,
        }
        with self.assertRaisesRegex(ValidationError, "case_mode=compatibility"):
            validate_case(case)
        report = evaluate_run(_base_run(), _base_case(min_score=0))
        self.assertEqual(report.case_mode, "quality")
        self.assertFalse(report.derived_expectations)

    def test_compatibility_report_marks_derived_expectations(self) -> None:
        case = _base_case(
            case_mode="compatibility",
            derive_entities_from_run=True,
            expected_entities=[],
            min_score=0,
        )
        report = evaluate_run(_base_run(), case)
        self.assertEqual(report.case_mode, "compatibility")
        self.assertTrue(report.derived_expectations)


class FinRunNestedValidationTestCase(unittest.TestCase):
    def test_rejects_illegal_nested_structures(self) -> None:
        cases = (
            ({"entities": [None]}, "entities\\[0\\]"),
            ({"entities": [{}]}, "entities\\[0\\]"),
            ({"steps": ["retrieval"]}, "steps\\[0\\]"),
            ({"metrics": ["bad"]}, "metrics\\[0\\]"),
            (
                {
                    "metrics": [
                        {
                            "entity": "A",
                            "name": "x",
                            "value": float("nan"),
                            "inputs": {"a": 1},
                        }
                    ]
                },
                "metrics\\[0\\]\\.value",
            ),
            (
                {
                    "metrics": [
                        {
                            "entity": "A",
                            "name": "x",
                            "value": float("inf"),
                            "inputs": {"a": 1},
                        }
                    ]
                },
                "metrics\\[0\\]\\.value",
            ),
            (
                {
                    "metrics": [
                        {
                            "entity": "A",
                            "name": "x",
                            "value": 1,
                            "inputs": [],
                        }
                    ]
                },
                "inputs must be an object",
            ),
            (
                {
                    "metrics": [
                        {
                            "entity": "A",
                            "name": "x",
                            "value": 1,
                            "inputs": {"a": float("nan")},
                        }
                    ]
                },
                "inputs\\.a",
            ),
            ({"evidence": ["bad"]}, "evidence\\[0\\]"),
            ({"market_data": [None]}, "market_data\\[0\\]"),
            ({"claims": ["bad"]}, "claims\\[0\\]"),
            (
                {"claims": [{"entity": "A", "value": float("inf")}]},
                "claims\\[0\\]\\.value",
            ),
        )
        for overrides, pattern in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValidationError, pattern):
                    validate_finrun(_base_run(**overrides))

    def test_official_fixtures_remain_compatible(self) -> None:
        for name in (
            "pass_finrun.json",
            "pass_due_diligence_finrun.json",
            "pass_bigtech_finrun.json",
            "fail_finrun.json",
            "fail_due_diligence_finrun.json",
        ):
            with self.subTest(name=name):
                validate_finrun(load_fixture(name))


class ScoreInvariantTestCase(unittest.TestCase):
    def test_non_finite_metric_scores_fail_closed(self) -> None:
        case = _base_case(min_score=0)
        for bad in (float("nan"), float("inf"), -1.0, 101.0):
            with self.subTest(score=bad):
                with self.assertRaises(ValidationError):
                    _score_results(
                        [MetricResult("entity_coverage", bad, False, [])],
                        case,
                    )

    def test_aggregate_score_stays_finite_0_to_100(self) -> None:
        report = evaluate_run(_base_run(), _base_case(min_score=0))
        self.assertTrue(math.isfinite(report.score))
        self.assertGreaterEqual(report.score, 0)
        self.assertLessEqual(report.score, 100)


class DerivedEntityBoundaryTestCase(unittest.TestCase):
    def test_quality_case_cannot_derive_entities(self) -> None:
        with self.assertRaisesRegex(ValidationError, "case_mode=compatibility"):
            validate_case(
                _base_case(
                    case_mode="quality",
                    derive_entities_from_run=True,
                    expected_entities=[],
                )
            )

    def test_compatibility_case_can_derive_entities(self) -> None:
        validate_case(
            _base_case(
                case_mode="compatibility",
                derive_entities_from_run=True,
                expected_entities=[],
            )
        )

    def test_quality_case_with_fixed_entities_allowed(self) -> None:
        validate_case(_base_case(case_mode="quality", expected_entities=["Apple"]))

    def test_compare_runs_freezes_derived_expectations_from_baseline(self) -> None:
        baseline = _base_run(
            run_id="base",
            entities=[{"name": "Apple"}, {"name": "Microsoft"}],
        )
        current = _base_run(
            run_id="current",
            entities=[{"name": "Apple"}],
        )
        case = _base_case(
            case_mode="compatibility",
            derive_entities_from_run=True,
            expected_entities=[],
            enabled_metrics=["entity_coverage"],
            min_score=100,
            regression_tolerance=0,
        )
        result = compare_runs(baseline, current, case)
        self.assertIn("entity_coverage", result["regressions"])
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
