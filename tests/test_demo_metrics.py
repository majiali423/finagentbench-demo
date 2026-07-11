from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import compare_runs, evaluate_run
from tests.helpers import load_fixture


class FinAgentBenchDemoTestCase(unittest.TestCase):
    def test_pass_fixture_passes(self) -> None:
        report = evaluate_run(load_fixture("pass_finrun.json"), load_fixture("case_compare_rd.json"))
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)

    def test_fail_fixture_fails(self) -> None:
        report = evaluate_run(load_fixture("fail_finrun.json"), load_fixture("case_compare_rd.json"))
        self.assertFalse(report.passed)
        findings = [finding.message for metric in report.metrics for finding in metric.findings]
        self.assertTrue(any("AMD" in finding for finding in findings))
        self.assertTrue(any("guaranteed return" in finding for finding in findings))

    def test_compare_detects_regression(self) -> None:
        payload = compare_runs(
            load_fixture("pass_finrun.json"),
            load_fixture("fail_finrun.json"),
            load_fixture("case_compare_rd.json"),
        )
        self.assertFalse(payload["passed"])
        self.assertIn("entity_coverage", payload["regressions"])


if __name__ == "__main__":
    unittest.main()
