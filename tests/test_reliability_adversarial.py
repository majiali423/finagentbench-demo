"""Adversarial / false-positive corpus for visible_output_integrity and value bounds."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.benchmark import run_benchmark_suite
from finagentbench.metrics.visible_output_integrity import visible_output_integrity
from finagentbench.provenance import case_hash
from finagentbench.schema import validate_case


ROOT = Path(__file__).resolve().parents[1]


def _run(output: str, entities: list[str] | None = None, **extra: object) -> dict:
    return {
        "run_id": "output-integrity-adv",
        "entities": [{"name": name} for name in (entities or ["Apple"])],
        "steps": [],
        "metrics": [],
        "evidence": [],
        "market_data": [],
        "final_output": output,
        **extra,
    }


class VisibleOutputIntegrityFalsePositiveTestCase(unittest.TestCase):
    def test_management_quote_need_to_passes(self) -> None:
        result = visible_output_integrity(
            _run('Management said, "we need to invest in capacity."'),
            {},
        )
        self.assertTrue(result.passed)

    def test_business_need_to_raise_capital_passes(self) -> None:
        result = visible_output_integrity(
            _run("The company may need to raise capital."),
            {},
        )
        self.assertTrue(result.passed)

    def test_code_block_lets_draft_passes(self) -> None:
        result = visible_output_integrity(
            _run("```\nlet's draft the checklist\n```\n\nDone."),
            {},
        )
        self.assertTrue(result.passed)

    def test_blockquote_prompt_restatement_passes_by_default(self) -> None:
        result = visible_output_integrity(
            _run("> the user asked for a memo\n\nThe memo is complete."),
            {},
        )
        self.assertTrue(result.passed)

    def test_true_reasoning_leak_still_fails(self) -> None:
        result = visible_output_integrity(
            _run("We need to draft the final answer."),
            {},
        )
        self.assertFalse(result.passed)

    def test_table_end_passes(self) -> None:
        output = (
            "# Comparison\n\n## Financials\n\n"
            "| Metric | Value |\n| --- | --- |\n| Revenue | 100 |\n"
        )
        self.assertTrue(visible_output_integrity(_run(output), {}).passed)

    def test_heading_with_only_table_passes(self) -> None:
        output = "## Peer Comparison\n\n| Company | Margin |\n| --- | --- |\n| Apple | 30% |\n"
        self.assertTrue(visible_output_integrity(_run(output, ["Apple"]), {}).passed)

    def test_heading_with_only_list_passes(self) -> None:
        output = "## Risks\n\n- Supplier concentration\n- FX exposure\n"
        self.assertTrue(visible_output_integrity(_run(output), {}).passed)

    def test_unclosed_code_block_fails(self) -> None:
        result = visible_output_integrity(_run("Intro\n\n```\nnot closed"), {})
        self.assertFalse(result.passed)
        self.assertTrue(any("code" in f.message.lower() for f in result.findings))

    def test_chinese_peer_alias(self) -> None:
        case = {
            "peer_section_aliases": ["同业比较", "Peer Comparison"],
            "entity_aliases": {
                "Apple": ["Apple", "苹果"],
                "Microsoft": ["Microsoft", "微软"],
            },
        }
        output = "## 同业比较\n\n苹果与微软利润率不同。\n\n## 结论\n\n比较完成。"
        result = visible_output_integrity(
            _run(output, ["Apple", "Microsoft"]),
            case,
        )
        self.assertTrue(result.passed)

    def test_ticker_alias_not_unknown(self) -> None:
        case = {"entity_aliases": {"Microsoft": ["Microsoft", "MSFT"]}}
        output = (
            "## Peer Comparison\n\nMSFT margin differs from the prior year.\n\n"
            "## Conclusion\n\nComplete."
        )
        result = visible_output_integrity(_run(output, ["Microsoft"]), case)
        self.assertTrue(result.passed)

    def test_lowercase_brand_not_auto_unknown(self) -> None:
        output = (
            "## Peer Comparison\n\nApple leads versus microsoft on reported margin.\n\n"
            "## Conclusion\n\nComplete."
        )
        # Heuristic guess of lowercase brand must not alone high-block when aliases cover it.
        case = {"entity_aliases": {"Microsoft": ["Microsoft", "microsoft", "MSFT"]}}
        result = visible_output_integrity(_run(output, ["Apple", "Microsoft"]), case)
        high = [f for f in result.findings if f.severity == "high"]
        self.assertFalse(any("outside FinRun entities" in f.message for f in high))

    def test_forbidden_entity_still_fails(self) -> None:
        result = visible_output_integrity(
            _run(
                "## Peer Comparison\n\nMicrosoft differs from Apple.\n\n## Conclusion\n\nDone.",
                ["Apple"],
            ),
            {"forbidden_entities": ["Microsoft"]},
        )
        self.assertFalse(result.passed)

    def test_table_end_without_period_passes(self) -> None:
        output = "# Report\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        self.assertTrue(visible_output_integrity(_run(output), {}).passed)

    def test_true_truncated_sentence_fails(self) -> None:
        result = visible_output_integrity(
            _run("## Peer Comparison\n\nWhich company leads"),
            {},
        )
        self.assertFalse(result.passed)

    def test_valid_corpus_fixtures_pass(self) -> None:
        case = json.loads(
            (ROOT / "fixtures" / "case_output_integrity_valid_corpus.json").read_text(
                encoding="utf-8"
            )
        )
        for name in (
            "output_integrity_valid_quotes_finrun.json",
            "output_integrity_table_end_finrun.json",
            "output_integrity_chinese_finrun.json",
            "output_integrity_ticker_alias_finrun.json",
            "output_integrity_code_blockquote_finrun.json",
        ):
            run = json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))
            with self.subTest(name=name):
                result = visible_output_integrity(run, case)
                self.assertTrue(result.passed, msg=[f.message for f in result.findings])

    def test_legacy_failure_fixtures_still_fail(self) -> None:
        case = json.loads(
            (ROOT / "fixtures" / "case_output_integrity.json").read_text(encoding="utf-8")
        )
        for name in (
            "output_integrity_reasoning_leak_finrun.json",
            "output_integrity_truncated_finrun.json",
        ):
            run = json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))
            with self.subTest(name=name):
                self.assertFalse(visible_output_integrity(run, case).passed)


class InputValueBoundsAdversarialTestCase(unittest.TestCase):
    def test_input_value_plausibility_module_contract(self) -> None:
        try:
            from finagentbench.metrics.input_value_plausibility import (
                input_value_plausibility,
            )
        except ImportError:
            self.fail("input_value_plausibility not implemented yet")

        run = {
            "run_id": "bounds",
            "entities": ["Microsoft"],
            "steps": [],
            "metrics": [
                {
                    "entity": "Microsoft",
                    "name": "operating_margin",
                    "value": 0.4,
                    "inputs": {
                        "revenue": {
                            "value": 245.0,
                            "unit": "billion_usd",
                            "currency": "USD",
                        },
                        "operating_income": {
                            "value": -5000.0,
                            "unit": "billion_usd",
                            "currency": "USD",
                        },
                    },
                }
            ],
            "evidence": [],
            "market_data": [],
            "final_output": "x",
        }
        case = {
            "enabled_metrics": ["input_value_plausibility"],
            "input_value_bounds": {
                "operating_income": {"unit": "billion_usd", "min": -500, "max": 500},
                "revenue": {"unit": "billion_usd", "min": 0, "max": 1000},
            },
        }
        result = input_value_plausibility(run, case)
        self.assertFalse(result.passed)
        self.assertTrue(
            any("outside case-configured bounds" in f.message for f in result.findings)
        )
        self.assertFalse(any("millions labeled" in f.message.lower() for f in result.findings))

    def test_no_bounds_means_no_plausibility_check(self) -> None:
        try:
            from finagentbench.metrics.input_value_plausibility import (
                input_value_plausibility,
            )
        except ImportError:
            self.fail("input_value_plausibility not implemented yet")

        run = {
            "run_id": "no-bounds",
            "entities": ["Microsoft"],
            "steps": [],
            "metrics": [
                {
                    "entity": "Microsoft",
                    "name": "x",
                    "value": 1,
                    "inputs": {
                        "revenue": {"value": 5000.0, "unit": "billion_usd", "currency": "USD"}
                    },
                }
            ],
            "evidence": [],
            "market_data": [],
            "final_output": "x",
        }
        result = input_value_plausibility(run, {"enabled_metrics": ["input_value_plausibility"]})
        self.assertTrue(result.passed)

    def test_case_hash_changes_with_bounds(self) -> None:
        base = {
            "id": "bounds-hash",
            "scoring_version": "2",
            "expected_entities": [],
            "required_steps": [],
        }
        with_bounds = {
            **base,
            "input_value_bounds": {"revenue": {"unit": "billion_usd", "min": 0, "max": 1000}},
        }
        validate_case(base)
        # Schema must accept new fields once implemented; until then validate may ignore.
        try:
            validate_case(with_bounds)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"validate_case must accept input_value_bounds: {exc}")
        self.assertNotEqual(case_hash(base), case_hash(with_bounds))

    def test_unit_currency_has_no_hardcoded_ceiling_constant(self) -> None:
        import finagentbench.metrics.unit_currency as mod

        self.assertFalse(
            hasattr(mod, "_ABSURD_BILLION_USD_CEILING"),
            "hardcoded absurd ceiling must be removed from unit_currency",
        )


class OutputIntegritySuiteExpansionTestCase(unittest.TestCase):
    def test_valid_corpus_fixture_files_exist(self) -> None:
        for name in (
            "output_integrity_valid_quotes_finrun.json",
            "output_integrity_table_end_finrun.json",
            "output_integrity_chinese_finrun.json",
            "output_integrity_ticker_alias_finrun.json",
            "output_integrity_code_blockquote_finrun.json",
            "case_output_integrity_valid_corpus.json",
        ):
            self.assertTrue((ROOT / "fixtures" / name).is_file(), msg=name)


if __name__ == "__main__":
    unittest.main()
