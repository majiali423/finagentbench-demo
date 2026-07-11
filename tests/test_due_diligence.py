from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file
from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture


ROOT = Path(__file__).resolve().parents[1]


class DueDiligenceTestCase(unittest.TestCase):
    def test_due_diligence_pass_fixture_passes(self) -> None:
        report = evaluate_run(load_fixture("pass_due_diligence_finrun.json"), load_fixture("case_due_diligence.json"))
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)

    def test_due_diligence_fail_fixture_fails(self) -> None:
        report = evaluate_run(load_fixture("fail_due_diligence_finrun.json"), load_fixture("case_due_diligence.json"))
        self.assertFalse(report.passed)
        findings = [finding.message for metric in report.metrics for finding in metric.findings]
        self.assertTrue(any("section" in finding.lower() for finding in findings))
        self.assertTrue(any("Forbidden financial language" in finding for finding in findings))

    def test_due_diligence_adapter_maps_state(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "due_diligence_state_sample.json", "due-diligence")
        report = evaluate_run(run, load_fixture("case_due_diligence.json"))
        self.assertTrue(report.passed)
        self.assertEqual(run["entities"][0]["name"], "TargetCo")


if __name__ == "__main__":
    unittest.main()
