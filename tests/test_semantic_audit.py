from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class SemanticAuditTestCase(unittest.TestCase):
    def test_static_judge_can_pass_evidence_support(self) -> None:
        case = _semantic_case(
            {
                "score": 92,
                "passed": True,
                "rationale": "The conclusion is supported by the cited balance-sheet evidence.",
                "severity": "low",
                "labels": ["supported"],
            }
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertTrue(metric.passed)
        self.assertEqual(metric.score, 92)

    def test_static_judge_can_fail_unsupported_claims(self) -> None:
        case = _semantic_case(
            {
                "score": 45,
                "passed": False,
                "rationale": "The conclusion adds an acquisition recommendation not present in evidence.",
                "severity": "high",
                "labels": ["unsupported_recommendation"],
            }
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertFalse(metric.passed)
        self.assertEqual(metric.findings[0].target["section"], "final_output")
        self.assertIn("unsupported_recommendation", metric.findings[0].target["labels"])

    def test_unconfigured_external_judge_degrades_to_finding(self) -> None:
        case = _load("case_due_diligence.json")
        case["enabled_metrics"] = ["evidence_support"]
        case["semantic_audit"] = {
            "judge": {"provider": "openai-compatible"},
            "min_evidence_support_score": 80,
        }
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertFalse(metric.passed)
        self.assertIn("missing endpoint", metric.findings[0].message.lower())


def _semantic_case(result: dict) -> dict:
    case = _load("case_due_diligence.json")
    case["enabled_metrics"] = ["evidence_support"]
    case["semantic_audit"] = {
        "judge": {
            "provider": "static",
            "results": {"evidence_support": result},
        },
        "min_evidence_support_score": 80,
    }
    return case


def _metric(report, name: str):
    return next(metric for metric in report.metrics if metric.name == name)


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
