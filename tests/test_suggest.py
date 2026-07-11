from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.runner import evaluate_run
from finagentbench.suggest import build_suggestions


ROOT = Path(__file__).resolve().parents[1]


class SuggestTestCase(unittest.TestCase):
    def test_findings_are_converted_to_actions(self) -> None:
        report = evaluate_run(_load("fail_due_diligence_finrun.json"), _load("case_due_diligence.json"))
        payload = build_suggestions(report)

        self.assertEqual(payload["run_id"], "fail-dd-targetco")
        actions = {item["action"] for item in payload["actions"]}
        self.assertIn("recompute", actions)
        self.assertIn("rewrite", actions)
        self.assertTrue(any(item["target"].get("section") == "final_output" for item in payload["actions"]))

    def test_lumenfin_regression_suggests_recompute_and_rewrite(self) -> None:
        report = evaluate_run(_load("lumenfin_regression_bad_finrun.json"), _load("case_lumenfin_diligence.json"))
        payload = build_suggestions(report)

        self.assertFalse(report.passed)
        actions = {item["action"] for item in payload["actions"]}
        self.assertIn("recompute", actions)
        self.assertIn("rewrite", actions)


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
