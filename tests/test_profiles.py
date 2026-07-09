from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
