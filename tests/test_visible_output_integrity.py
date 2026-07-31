from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.benchmark import run_benchmark_suite
from finagentbench.metrics.visible_output_integrity import visible_output_integrity
from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


def _run(output: str, entities: list[str] | None = None, **extra: object) -> dict:
    return {
        "run_id": "output-integrity-test",
        "entities": [{"name": name} for name in (entities or ["Apple", "Microsoft"])],
        "steps": [],
        "metrics": [],
        "evidence": [],
        "market_data": [],
        "final_output": output,
        **extra,
    }


class VisibleOutputIntegrityTestCase(unittest.TestCase):
    def test_clean_output_passes(self) -> None:
        result = visible_output_integrity(
            _run(
                "# Report\n\n## Peer Comparison\n\n"
                "Apple and Microsoft have different growth and margin profiles.\n\n"
                "## Conclusion\n\nThe evidence supports a cautious comparison."
            ),
            {},
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 100.0)

    def test_reasoning_markers_are_bounded_and_case_insensitive(self) -> None:
        for phrase in (
            "WE NEED TO summarize.",
            "Let's Draft the answer.",
            "The instruction says to compare.",
            "The user asked for a report.",
            "I need to finish.",
            "We must comply.",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(visible_output_integrity(_run(phrase), {}).passed)
        for clean in ("The company may need capital.", "A draft filing was published.", "Instruction quality matters."):
            with self.subTest(clean=clean):
                self.assertTrue(visible_output_integrity(_run(clean), {}).passed)

    def test_only_final_output_is_inspected_for_reasoning(self) -> None:
        run = _run("The report is complete.", metadata={"reasoning": "We need to draft."})
        self.assertTrue(visible_output_integrity(run, {}).passed)

    def test_truncated_peer_section_and_unpunctuated_end_fail(self) -> None:
        result = visible_output_integrity(
            _run("# Report\n\n## Peer Comparison\n\nWhich company leads"), {}
        )
        messages = [finding.message for finding in result.findings]
        self.assertTrue(any("truncated" in message for message in messages))
        self.assertFalse(result.passed)

    def test_heading_without_prose_fails(self) -> None:
        result = visible_output_integrity(_run("# Report\n\n## Empty"), {})
        self.assertTrue(any("no following prose" in finding.message for finding in result.findings))

    def test_single_company_leadership_claim_fails(self) -> None:
        result = visible_output_integrity(
            _run(
                "## Peer Comparison\n\nApple leads the selected peer group on reported margin.\n\n"
                "## Conclusion\n\nThe comparison is complete.",
                ["Apple"],
            ),
            {},
        )
        self.assertTrue(any("Single-company" in finding.message for finding in result.findings))

    def test_unknown_peer_company_fails(self) -> None:
        result = visible_output_integrity(
            _run(
                "## Peer Comparison\n\nApple differs versus Microsoft on the selected metric.\n\n"
                "## Conclusion\n\nThe comparison is complete.",
                ["Apple"],
            ),
            {},
        )
        # Regex-guessed unknown peers are medium findings and do not alone high-block.
        self.assertTrue(any("Microsoft" in finding.message for finding in result.findings))
        self.assertTrue(result.passed)

    def test_forbidden_company_is_found_without_leadership_language(self) -> None:
        result = visible_output_integrity(
            _run(
                "## Peer Comparison\n\nMicrosoft has a different margin profile from Apple.\n\n"
                "## Conclusion\n\nThe comparison is complete.",
                ["Apple"],
            ),
            {"forbidden_entities": ["Microsoft"]},
        )
        self.assertTrue(any("Microsoft" in finding.message for finding in result.findings))

    def test_prompt_restatement_fails(self) -> None:
        result = visible_output_integrity(_run("The prompt asks us to compare the issuers."), {})
        self.assertTrue(any("restatement" in finding.message for finding in result.findings))

    def test_zero_weight_preserves_clean_score_and_high_finding_blocks(self) -> None:
        case = {
            "scoring_version": "2",
            "expected_entities": [],
            "required_steps": [],
            "enabled_metrics": ["visible_output_integrity"],
            "metric_weights": {"visible_output_integrity": 0},
            "min_score": 85,
            "block_on_severity": ["high", "critical"],
        }
        clean = evaluate_run(_run("The report is complete."), case)
        leaked = evaluate_run(_run("We need to write the report."), case)
        self.assertEqual(clean.score, 100.0)
        self.assertTrue(clean.passed)
        self.assertFalse(leaked.passed)

    def test_output_integrity_benchmark_detects_both_failures(self) -> None:
        report = run_benchmark_suite(ROOT / "benchmarks" / "output_integrity" / "suite.json")
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["expected_failures"], 2)
        self.assertEqual(report["detected_failures"], report["expected_failures"])
        self.assertEqual(report["false_positives"], 0)

    def test_metric_is_v2_only_in_versioned_fixtures(self) -> None:
        v1 = json.loads(
            (ROOT / "fixtures" / "case_lumenfin_issuer_aapl.json").read_text(encoding="utf-8")
        )
        v2 = json.loads(
            (ROOT / "fixtures" / "case_output_integrity.json").read_text(encoding="utf-8")
        )
        self.assertEqual(v1.get("scoring_version", "1"), "1")
        self.assertNotIn("visible_output_integrity", v1["enabled_metrics"])
        self.assertEqual(v2["scoring_version"], "2")
        self.assertIn("visible_output_integrity", v2["enabled_metrics"])


if __name__ == "__main__":
    unittest.main()
