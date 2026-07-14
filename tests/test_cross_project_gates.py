from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file
from finagentbench.metrics.input_safety import input_safety
from finagentbench.metrics.retrieval_provenance import retrieval_provenance
from finagentbench.metrics.runtime_compliance import runtime_compliance
from finagentbench.runner import evaluate_run
from tests.helpers import load_fixture, metric_by_name


ROOT = Path(__file__).resolve().parents[1]


class CrossProjectGateTestCase(unittest.TestCase):
    def test_lumenfin_adapter_exports_cross_project_metadata(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        metadata = run["metadata"]

        self.assertEqual(metadata["data_mode"], "demo")
        self.assertTrue(metadata["input_guardrail_summary"]["allowed"])
        self.assertEqual(metadata["compliance_violations"], [])
        self.assertEqual(metadata["retrieval_provenance"]["Apple"]["structured_source"], "sample_db")

        metric = next(item for item in run["metrics"] if item["entity"] == "Apple")
        self.assertEqual(metric["confidence"]["structured_source"], "sample_db")
        self.assertAlmostEqual(metric["confidence"]["retrieval_overall"], 0.83)

    def test_runtime_compliance_fails_when_unexpected_violation_exported(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        run["metadata"]["compliance_violations"] = [
            {"code": "missing_quantitative_results", "severity": "high", "message": "Apple gap"}
        ]
        case = {
            "expected_entities": ["Apple", "Microsoft"],
            "required_steps": [],
            "expected_violation_codes": [],
            "enabled_metrics": ["runtime_compliance"],
        }

        result = runtime_compliance(run, case)

        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].metric, "runtime_compliance")
        self.assertIn("missing_quantitative_results", result.findings[0].message)

    def test_retrieval_provenance_fails_live_mode_without_structured_data(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        run["metadata"]["data_mode"] = "live"
        run["metadata"]["retrieval_provenance"] = {
            "Apple": {"structured_source": "none", "data_mode": "live"},
            "Microsoft": {"structured_source": "document_extracted", "data_mode": "live"},
        }
        for metric in run["metrics"]:
            if metric["entity"] == "Apple":
                metric["confidence"]["structured_source"] = "none"
                metric["confidence"]["retrieval_overall"] = 0.1
            if metric["entity"] == "Microsoft":
                metric["confidence"]["structured_source"] = "document_extracted"
                metric["confidence"]["retrieval_overall"] = 0.8

        case = {
            "expected_entities": ["Apple", "Microsoft"],
            "required_steps": [],
            "require_retrieval_provenance": True,
            "data_mode": "live",
            "forbidden_structured_sources": ["none"],
            "min_retrieval_confidence": 0.35,
            "enabled_metrics": ["retrieval_provenance"],
        }

        result = retrieval_provenance(run, case)

        self.assertFalse(result.passed)
        messages = " ".join(finding.message for finding in result.findings)
        self.assertIn("Apple", messages)
        self.assertIn("structured_source=none", messages)

    def test_input_safety_flags_blocked_guardrail_runs(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        run["metadata"]["workflow_status"] = "blocked_by_guardrail"
        run["metadata"]["input_guardrail_summary"] = {
            "allowed": False,
            "mode": "block",
            "finding_count": 2,
            "critical_count": 2,
        }
        case = {
            "expected_entities": [],
            "required_steps": [],
            "require_input_guardrail": True,
            "enabled_metrics": ["input_safety"],
        }

        result = input_safety(run, case)

        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].severity, "critical")

    def test_diligence_case_includes_cross_project_metrics_by_default(self) -> None:
        case = load_fixture("case_lumenfin_diligence.json")
        self.assertIn("input_safety", case["enabled_metrics"])
        self.assertIn("runtime_compliance", case["enabled_metrics"])
        self.assertIn("retrieval_provenance", case["enabled_metrics"])
        self.assertTrue(case.get("require_input_guardrail"))
        self.assertEqual(case.get("expected_violation_codes"), [])

    def test_diligence_case_passes_clean_fixture_with_cross_project_metrics(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        case = load_fixture("case_lumenfin_diligence.json")

        report = evaluate_run(run, case)

        self.assertTrue(metric_by_name(report, "input_safety").passed)
        self.assertTrue(metric_by_name(report, "runtime_compliance").passed)
        self.assertTrue(metric_by_name(report, "retrieval_provenance").passed)
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
