from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.runner import compare_runs, evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class FinAgentBenchDemoTestCase(unittest.TestCase):
    def test_pass_fixture_passes(self) -> None:
        report = evaluate_run(_load("pass_finrun.json"), _load("case_compare_rd.json"))
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)

    def test_fail_fixture_fails(self) -> None:
        report = evaluate_run(_load("fail_finrun.json"), _load("case_compare_rd.json"))
        self.assertFalse(report.passed)
        findings = [finding.message for metric in report.metrics for finding in metric.findings]
        self.assertTrue(any("AMD" in finding for finding in findings))
        self.assertTrue(any("guaranteed return" in finding for finding in findings))

    def test_compare_detects_regression(self) -> None:
        payload = compare_runs(_load("pass_finrun.json"), _load("fail_finrun.json"), _load("case_compare_rd.json"))
        self.assertFalse(payload["passed"])
        self.assertIn("entity_coverage", payload["regressions"])


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
