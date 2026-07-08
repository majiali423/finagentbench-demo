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


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
