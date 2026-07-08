from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.adapters import load_run_file
from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class DueDiligenceTestCase(unittest.TestCase):
    def test_due_diligence_pass_fixture_passes(self) -> None:
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), _load("case_due_diligence.json"))
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)

    def test_due_diligence_fail_fixture_fails(self) -> None:
        report = evaluate_run(_load("fail_due_diligence_finrun.json"), _load("case_due_diligence.json"))
        self.assertFalse(report.passed)
        findings = [finding.message for metric in report.metrics for finding in metric.findings]
        self.assertTrue(any("section" in finding.lower() for finding in findings))
        self.assertTrue(any("Forbidden financial language" in finding for finding in findings))

    def test_due_diligence_adapter_maps_state(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "due_diligence_state_sample.json", "due-diligence")
        report = evaluate_run(run, _load("case_due_diligence.json"))
        self.assertTrue(report.passed)
        self.assertEqual(run["entities"][0]["name"], "TargetCo")


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
