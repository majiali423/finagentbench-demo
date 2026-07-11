from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file
from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture, metric_by_name


ROOT = Path(__file__).resolve().parents[1]


class LumenFinIntegrationTestCase(unittest.TestCase):
    def test_lumenfin_state_passes_diligence_case(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        case = load_fixture("case_lumenfin_diligence.json")

        report = evaluate_run(run, case)

        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 85)
        self.assertTrue(metric_by_name(report, "numeric_correctness").passed)
        self.assertTrue(metric_by_name(report, "evidence_consistency").passed)
        self.assertEqual(metric_by_name(report, "entity_coverage").findings, [])
        self.assertEqual(metric_by_name(report, "step_presence").findings, [])
        self.assertEqual(metric_by_name(report, "section_presence").findings, [])

    def test_lumenfin_case_accepts_live_report_risk_language(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        run["final_output"] = run["final_output"].replace("## Risk", "Risk Exposure Matrix")
        run["final_output"] = run["final_output"].replace(
            "not investment advice",
            "does not constitute investment advice",
        )
        run["final_output"] += "\n_Source: LLM knowledge (unverified in this run)._"
        case = load_fixture("case_lumenfin_diligence.json")

        report = evaluate_run(run, case)

        findings = [finding.metric for metric in report.metrics for finding in metric.findings]
        self.assertNotIn("section_presence", findings)
        self.assertNotIn("risk_disclosure", findings)

if __name__ == "__main__":
    unittest.main()
