from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class EvidenceConsistencyTestCase(unittest.TestCase):
    def test_evidence_consistency_passes_when_numbers_match(self) -> None:
        report = evaluate_run(_load("pass_bigtech_finrun.json"), _load("case_bigtech_fcf.json"))
        metric = _metric(report, "evidence_consistency")
        self.assertTrue(metric.passed)
        self.assertEqual(metric.score, 100.0)

    def test_evidence_consistency_fails_when_citation_numbers_disagree(self) -> None:
        run = _load("pass_bigtech_finrun.json")
        case = _load("case_bigtech_fcf.json")
        run["evidence"][0]["text"] = "AAPL free cash flow was 80.0 billion USD and revenue was 382.7 billion USD."

        report = evaluate_run(run, case)

        metric = _metric(report, "evidence_consistency")
        self.assertFalse(metric.passed)
        self.assertTrue(any("free_cash_flow" in finding.message for finding in metric.findings))


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def _metric(report, name: str):
    for metric in report.metrics:
        if metric.name == name:
            return metric
    raise AssertionError(f"metric not found: {name}")


if __name__ == "__main__":
    unittest.main()
