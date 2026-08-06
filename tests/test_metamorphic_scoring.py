"""Metamorphic / anti-gaming invariants for FinAgentBench scoring.

These tests assert scoring algebra properties. They are not ablation studies.
"""

from __future__ import annotations

import copy
import random
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.metrics.entity import entity_coverage, entity_leakage
from finagentbench.metrics.evidence import evidence_coverage
from finagentbench.metrics.evidence_consistency import evidence_consistency
from finagentbench.metrics.numeric import numeric_correctness
from finagentbench.metrics.risk import risk_disclosure
from finagentbench.runner import evaluate_run
from finagentbench.schema import validate_finrun


def _scores(report) -> dict[str, float]:
    return {metric.name: metric.score for metric in report.metrics}


def _base_run() -> dict:
    return {
        "run_id": "meta-demo",
        "schema_version": "1.0",
        "entities": [{"name": "NVIDIA"}, {"name": "AMD"}],
        "steps": [
            {"name": "retrieval", "status": "ok"},
            {"name": "quant", "status": "ok"},
        ],
        "metrics": [
            {
                "entity": "NVIDIA",
                "name": "r_and_d_intensity",
                "value": 0.098084,
                "period": "FY2025",
                "unit": "ratio",
                "currency": "USD",
                "formula": "r_and_d / revenue",
                "inputs": {
                    "r_and_d": {
                        "value": 12.8,
                        "unit": "billion",
                        "currency": "USD",
                        "period": "FY2025",
                    },
                    "revenue": {
                        "value": 130.5,
                        "unit": "billion",
                        "currency": "USD",
                        "period": "FY2025",
                    },
                },
            },
            {
                "entity": "AMD",
                "name": "r_and_d_intensity",
                "value": 0.25,
                "period": "FY2025",
                "formula": "r_and_d / revenue",
                "inputs": {"r_and_d": 6.5, "revenue": 26.0},
            },
        ],
        "evidence": [
            {
                "entity": "NVIDIA",
                "citation": "nvidia.pdf#1",
                "period": "FY2025",
                "text": "Research and development expenses were 12.8 billion USD on revenue of 130.5 billion USD.",
            },
            {
                "entity": "AMD",
                "citation": "amd.pdf#1",
                "period": "FY2025",
                "text": "R&D expenses were 6.5 billion USD on revenue of 26.0 billion USD.",
            },
        ],
        "market_data": [
            {"entity": "NVIDIA", "status": "ok", "provider": "demo"},
            {"entity": "AMD", "status": "ok", "provider": "demo"},
        ],
        "claims": [
            {
                "entity": "NVIDIA",
                "metric_name": "r_and_d_intensity",
                "period": "FY2025",
                "value": 0.098084,
                "unit": "ratio",
                "verification": "verified",
            }
        ],
        "final_output": (
            "## Executive Summary\n"
            "NVIDIA and AMD comparison.\n"
            "## Risk\n"
            "Market risk and data limitations remain material. "
            "This is research output only and not investment advice.\n"
        ),
    }


def _base_case(**overrides) -> dict:
    case = {
        "case_mode": "quality",
        "expected_entities": ["NVIDIA", "AMD"],
        "forbidden_entities": ["Intel"],
        "required_steps": ["retrieval", "quant"],
        "enabled_metrics": [
            "entity_coverage",
            "entity_leakage",
            "numeric_correctness",
            "evidence_coverage",
            "evidence_consistency",
            "risk_disclosure",
        ],
        "require_evidence_consistency": True,
        "require_risk_disclosure": True,
        "required_risk_types": ["market", "data"],
        "numeric_tolerance": 0.001,
        "evidence_numeric_tolerance": 0.05,
        "min_score": 0,
    }
    case.update(overrides)
    return case


class MetamorphicScoringTestCase(unittest.TestCase):
    def test_permutation_of_collections_does_not_change_scores(self) -> None:
        # Order is not semantic for these FinRun collections; shuffling must be score-neutral.
        run = _base_run()
        case = _base_case()
        baseline = evaluate_run(run, case)
        rng = random.Random(7)
        shuffled = copy.deepcopy(run)
        for key in ("entities", "steps", "metrics", "evidence", "market_data", "claims"):
            rng.shuffle(shuffled[key])
        validate_finrun(shuffled)
        report = evaluate_run(shuffled, case)
        self.assertEqual(_scores(baseline), _scores(report))
        self.assertEqual(baseline.passed, report.passed)

    def test_removing_supporting_evidence_does_not_raise_evidence_scores(self) -> None:
        run = _base_run()
        case = _base_case()
        before_cov = evidence_coverage(run, case).score
        before_cons = evidence_consistency(run, case).score
        degraded = copy.deepcopy(run)
        degraded["evidence"] = [item for item in degraded["evidence"] if item["entity"] != "NVIDIA"]
        after_cov = evidence_coverage(degraded, case).score
        after_cons = evidence_consistency(degraded, case).score
        self.assertLess(after_cov, before_cov)
        self.assertLess(after_cons, before_cons)

    def test_larger_numeric_error_does_not_raise_numeric_score(self) -> None:
        case = _base_case(enabled_metrics=["numeric_correctness"])
        exact = _base_run()
        small = copy.deepcopy(exact)
        small["metrics"][0]["value"] = 0.11
        large = copy.deepcopy(exact)
        large["metrics"][0]["value"] = 0.50
        scores = [
            numeric_correctness(exact, case).score,
            numeric_correctness(small, case).score,
            numeric_correctness(large, case).score,
        ]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreater(scores[0], scores[1])
        self.assertGreaterEqual(scores[1], scores[2])

    def test_adding_forbidden_entity_does_not_raise_entity_scores(self) -> None:
        run = _base_run()
        case = _base_case()
        before_cov = entity_coverage(run, case).score
        before_leak = entity_leakage(run, case).score
        polluted = copy.deepcopy(run)
        polluted["entities"].append({"name": "Intel"})
        after_cov = entity_coverage(polluted, case).score
        after_leak = entity_leakage(polluted, case).score
        self.assertEqual(after_cov, before_cov)
        self.assertLess(after_leak, before_leak)
        run = _base_run()
        case = _base_case()
        before_cov = evidence_coverage(run, case).score
        before_cons = evidence_consistency(run, case).score
        spam = copy.deepcopy(run)
        for index in range(20):
            spam["evidence"].append(
                {
                    "entity": "UnrelatedCo",
                    "citation": f"spam.pdf#{index}",
                    "text": "Irrelevant boilerplate with no NVIDIA inputs.",
                }
            )
        after_cov = evidence_coverage(spam, case).score
        after_cons = evidence_consistency(spam, case).score
        self.assertLessEqual(after_cov, before_cov)
        self.assertLessEqual(after_cons, before_cons)

    def test_risk_heading_spam_does_not_satisfy_risk_disclosure(self) -> None:
        run = _base_run()
        run["final_output"] = "## Risk\n## Risk Analysis\n## Risk Matrix\n"
        case = _base_case(enabled_metrics=["risk_disclosure"])
        result = risk_disclosure(run, case)
        self.assertFalse(result.passed)
        self.assertLess(result.score, 100)

    def test_number_spam_with_mismatched_entity_fails_evidence_consistency(self) -> None:
        run = _base_run()
        run["evidence"] = [
            {
                "entity": "WrongEntity",
                "citation": "spam.pdf#1",
                "period": "FY1999",
                "text": (
                    "Numbers 12.8 130.5 6.5 26.0 0.098084 0.25 appear here but "
                    "entity/period/unit/metric context does not match NVIDIA FY2025."
                ),
            }
        ]
        case = _base_case(enabled_metrics=["evidence_consistency"])
        result = evidence_consistency(run, case)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)


if __name__ == "__main__":
    unittest.main()
