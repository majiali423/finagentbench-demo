from __future__ import annotations

import unittest
from pathlib import Path

from finagentbench.adapters import load_run_file
from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class LumenFinIntegrationTestCase(unittest.TestCase):
    def test_lumenfin_state_passes_diligence_case(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        case = load_run_case("case_lumenfin_diligence.json")

        report = evaluate_run(run, case)

        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)
        self.assertEqual({metric.name for metric in report.metrics} & {"numeric_correctness", "evidence_consistency"}, {"numeric_correctness", "evidence_consistency"})


def load_run_case(name: str) -> dict:
    import json

    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
