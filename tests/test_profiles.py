from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.profiles import apply_profile


class ProfileTestCase(unittest.TestCase):
    def test_ci_profile_removes_semantic_metrics(self) -> None:
        case = {
            "enabled_metrics": ["numeric_correctness", "evidence_support", "risk_quality"],
            "expected_entities": [],
            "required_steps": [],
        }

        profiled = apply_profile(case, "ci")

        self.assertEqual(profiled["enabled_metrics"], ["numeric_correctness"])
        self.assertEqual(profiled["semantic_profile"], "ci")
        self.assertIn("evidence_support", case["enabled_metrics"])

    def test_audit_profile_adds_configured_audit_metrics(self) -> None:
        case = {
            "enabled_metrics": ["numeric_correctness"],
            "audit_metrics": ["evidence_support", "compliance_semantic"],
            "expected_entities": [],
            "required_steps": [],
        }

        profiled = apply_profile(case, "audit")

        self.assertEqual(
            profiled["enabled_metrics"],
            ["numeric_correctness", "evidence_support", "compliance_semantic"],
        )
        self.assertEqual(profiled["semantic_profile"], "audit")

    def test_audit_profile_without_enabled_metrics_evaluates_only_audit_metrics(self) -> None:
        case = {
            "audit_metrics": ["evidence_support", "risk_quality"],
            "expected_entities": [],
            "required_steps": [],
        }

        profiled = apply_profile(case, "audit")

        self.assertEqual(profiled["enabled_metrics"], ["evidence_support", "risk_quality"])
        self.assertEqual(profiled["semantic_profile"], "audit")


if __name__ == "__main__":
    unittest.main()
