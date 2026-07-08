from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class RealisticFixtureTestCase(unittest.TestCase):
    def test_bigtech_fixture_passes_realistic_case(self) -> None:
        report = evaluate_run(_load("pass_bigtech_finrun.json"), _load("case_bigtech_fcf.json"))
        self.assertTrue(report.passed)
        self.assertEqual(report.score, 100.0)

    def test_temporal_mismatch_is_detected(self) -> None:
        run = _load("pass_bigtech_finrun.json")
        case = _load("case_bigtech_fcf.json")
        run["metrics"][0]["inputs"]["revenue"]["period"] = "FY2024"

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("mixes metric period" in finding for finding in findings))

    def test_unit_currency_mismatch_is_detected(self) -> None:
        run = _load("pass_bigtech_finrun.json")
        case = _load("case_bigtech_fcf.json")
        run["metrics"][1]["inputs"]["revenue"]["currency"] = "EUR"

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("mixed or missing currencies" in finding for finding in findings))

    def test_missing_risk_disclosure_is_detected(self) -> None:
        run = _load("pass_bigtech_finrun.json")
        case = _load("case_bigtech_fcf.json")
        run["final_output"] = "AAPL, MSFT, and NVDA were compared using cited annual filing evidence."

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("does not disclose material risks" in finding for finding in findings))


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def _finding_messages(report) -> list[str]:
    return [finding.message for metric in report.metrics for finding in metric.findings]


if __name__ == "__main__":
    unittest.main()
