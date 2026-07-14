from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture, metric_by_name


class RealisticFixtureTestCase(unittest.TestCase):
    def test_bigtech_fixture_passes_realistic_case(self) -> None:
        report = evaluate_run(load_fixture("pass_bigtech_finrun.json"), load_fixture("case_bigtech_fcf.json"))
        self.assertTrue(report.passed)
        self.assertEqual(report.score, 100.0)

    def test_temporal_mismatch_is_detected(self) -> None:
        run = load_fixture("pass_bigtech_finrun.json")
        case = load_fixture("case_bigtech_fcf.json")
        run["metrics"][0]["inputs"]["revenue"]["period"] = "FY2024"

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("mixes metric period" in finding for finding in findings))

    def test_unit_currency_mismatch_is_detected(self) -> None:
        run = load_fixture("pass_bigtech_finrun.json")
        case = load_fixture("case_bigtech_fcf.json")
        run["metrics"][1]["inputs"]["revenue"]["currency"] = "EUR"

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("mixed or missing currencies" in finding for finding in findings))

    def test_explicit_unit_currency_metric_runs_without_legacy_flag(self) -> None:
        run = load_fixture("pass_bigtech_finrun.json")
        case = load_fixture("case_bigtech_fcf.json")
        case.pop("require_unit_currency_consistency")
        case["enabled_metrics"] = ["unit_currency_consistency"]
        run["metrics"][1]["inputs"]["revenue"]["currency"] = "EUR"

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(report.passed)
        self.assertTrue(any("mixed or missing currencies" in finding for finding in findings))

    def test_missing_risk_disclosure_is_detected(self) -> None:
        run = load_fixture("pass_bigtech_finrun.json")
        case = load_fixture("case_bigtech_fcf.json")
        run["final_output"] = "AAPL, MSFT, and NVDA were compared using cited annual filing evidence."

        report = evaluate_run(run, case)

        findings = _finding_messages(report)
        self.assertFalse(metric_by_name(report, "risk_disclosure").passed)
        self.assertTrue(any("does not disclose material risks" in finding for finding in findings))


def _finding_messages(report) -> list[str]:
    return [finding.message for metric in report.metrics for finding in metric.findings]


if __name__ == "__main__":
    unittest.main()
