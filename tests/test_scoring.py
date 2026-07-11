from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import evaluate_run


class ScoringTestCase(unittest.TestCase):
    def test_metric_weights_affect_score(self) -> None:
        run = _minimal_run()
        case = {
            "expected_entities": ["A", "B"],
            "required_steps": [],
            "enabled_metrics": ["entity_coverage", "step_presence"],
            "metric_weights": {"entity_coverage": 3.0, "step_presence": 1.0},
            "min_score": 0,
        }

        report = evaluate_run(run, case)

        self.assertEqual(report.score, 62.5)

    def test_severity_penalty_reduces_score(self) -> None:
        run = _minimal_run()
        case = {
            "expected_entities": ["A", "B"],
            "required_steps": [],
            "enabled_metrics": ["entity_coverage"],
            "severity_penalties": {"high": 10},
            "min_score": 0,
        }

        report = evaluate_run(run, case)

        self.assertEqual(report.score, 40.0)


def _minimal_run() -> dict:
    return {
        "run_id": "scoring-demo",
        "entities": [{"name": "A"}],
        "steps": [],
        "metrics": [],
        "evidence": [],
        "market_data": [],
        "final_output": "Research output only and not investment advice.",
    }


if __name__ == "__main__":
    unittest.main()
