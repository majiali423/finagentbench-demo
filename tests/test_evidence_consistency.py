from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture, metric_by_name


class EvidenceConsistencyTestCase(unittest.TestCase):
    def test_evidence_consistency_passes_when_numbers_match(self) -> None:
        report = evaluate_run(load_fixture("pass_bigtech_finrun.json"), load_fixture("case_bigtech_fcf.json"))
        metric = metric_by_name(report, "evidence_consistency")
        self.assertTrue(metric.passed)
        self.assertEqual(metric.score, 100.0)

    def test_evidence_consistency_fails_when_citation_numbers_disagree(self) -> None:
        run = load_fixture("pass_bigtech_finrun.json")
        case = load_fixture("case_bigtech_fcf.json")
        run["evidence"][0]["text"] = "AAPL free cash flow was 80.0 billion USD and revenue was 382.7 billion USD."

        report = evaluate_run(run, case)

        metric = metric_by_name(report, "evidence_consistency")
        self.assertFalse(metric.passed)
        self.assertTrue(any("free_cash_flow" in finding.message for finding in metric.findings))


if __name__ == "__main__":
    unittest.main()
