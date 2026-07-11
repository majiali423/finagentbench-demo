from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.runner import evaluate_run
from finagentbench.suggest import build_suggestions
from tests.helpers import load_fixture


class SuggestTestCase(unittest.TestCase):
    def test_findings_are_converted_to_actions(self) -> None:
        report = evaluate_run(load_fixture("fail_due_diligence_finrun.json"), load_fixture("case_due_diligence.json"))
        payload = build_suggestions(report)

        self.assertEqual(payload["run_id"], "fail-dd-targetco")
        actions = {item["action"] for item in payload["actions"]}
        self.assertIn("recompute", actions)
        self.assertIn("rewrite", actions)
        self.assertTrue(any(item["target"].get("section") == "final_output" for item in payload["actions"]))

    def test_lumenfin_regression_suggests_recompute_and_rewrite(self) -> None:
        report = evaluate_run(
            load_fixture("lumenfin_regression_bad_finrun.json"),
            load_fixture("case_lumenfin_diligence.json"),
        )
        payload = build_suggestions(report)

        self.assertFalse(report.passed)
        actions = {item["action"] for item in payload["actions"]}
        self.assertIn("recompute", actions)
        self.assertIn("rewrite", actions)

if __name__ == "__main__":
    unittest.main()
