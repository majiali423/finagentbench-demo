from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file
from finagentbench.case_binding import resolve_case_for_run
from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture, metric_by_name


ROOT = Path(__file__).resolve().parents[1]


class GenericCaseTestCase(unittest.TestCase):
    def test_derive_entities_from_run_overrides_empty_case_list(self) -> None:
        run = {
            "run_id": "x",
            "final_output": "ok",
            "entities": [{"name": "NVIDIA"}, {"name": "AMD"}],
            "steps": [],
            "metrics": [],
            "evidence": [],
            "market_data": [],
        }
        case = {"expected_entities": [], "required_steps": [], "derive_entities_from_run": True}
        resolved = resolve_case_for_run(run, case)
        self.assertEqual(resolved["expected_entities"], ["NVIDIA", "AMD"])

    def test_generic_case_gates_arbitrary_entities_from_finrun(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        # Simulate a non-Apple real export by renaming entities in FinRun shape.
        run["entities"] = [{"name": "NVIDIA"}]
        run["metrics"] = [item for item in run["metrics"] if item["entity"] == "Apple"]
        for item in run["metrics"]:
            item["entity"] = "NVIDIA"
        run["evidence"] = [item for item in run["evidence"] if item.get("entity") == "Apple"][:2]
        for item in run["evidence"]:
            item["entity"] = "NVIDIA"
        run["market_data"] = [{"entity": "NVIDIA", "status": "ok", "provider": "fake"}]
        run["metadata"]["retrieval_provenance"] = {
            "NVIDIA": {"structured_source": "sample_db", "data_mode": "demo"}
        }
        case = load_fixture("case_lumenfin_generic.json")
        report = evaluate_run(run, case)
        self.assertEqual(
            resolve_case_for_run(run, case)["expected_entities"],
            ["NVIDIA"],
        )
        self.assertTrue(metric_by_name(report, "entity_coverage").passed)
        apple_mentions = [
            finding.message
            for metric in report.metrics
            for finding in metric.findings
            if "Apple" in finding.message and finding.metric == "entity_coverage"
        ]
        self.assertEqual(apple_mentions, [])

    def test_diligence_case_still_requires_apple_microsoft_for_regression(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        case = load_fixture("case_lumenfin_diligence.json")
        self.assertFalse(case.get("derive_entities_from_run"))
        report = evaluate_run(run, case)
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
