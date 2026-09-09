from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.benchmark import run_benchmark_suite
from finagentbench.metrics.visible_supported_claims import visible_supported_claims
from finagentbench.runner import evaluate_run
from finagentbench.schema import validate_case, validate_finrun


ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads(
    (ROOT / "fixtures" / "product_quality_visible_baseline_finrun.json").read_text(encoding="utf-8")
)
CASE = json.loads(
    (ROOT / "fixtures" / "case_lumenfin_product_quality_v1.json").read_text(encoding="utf-8")
)


def _case(**overrides: object) -> dict:
    payload = dict(CASE)
    payload.update(overrides)
    return payload


class VisibleSupportedClaimsTestCase(unittest.TestCase):
    def test_hand_authored_baseline_passes_and_ignores_ordinary_numbers(self) -> None:
        validate_finrun(BASELINE)
        validate_case(CASE)
        result = visible_supported_claims(BASELINE, CASE)
        self.assertTrue(result.passed, [item.message for item in result.findings])
        report = evaluate_run(BASELINE, CASE)
        self.assertTrue(report.passed)
        self.assertEqual(report.scoring_version, "3")

    def test_999999_percent_prose_is_blocked(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = BASELINE["final_output"] + "\nApple EBITDA margin is 999999% for FY2025.\n"
        result = visible_supported_claims(run, CASE)
        self.assertFalse(result.passed)
        self.assertTrue(any("999999" in item.message or "wrong_number" in str(item.target) for item in result.findings))

    def test_visible_output_integrity_still_misses_the_numeric_lie(self) -> None:
        from finagentbench.metrics.visible_output_integrity import visible_output_integrity

        run = dict(BASELINE)
        run["final_output"] = BASELINE["final_output"] + "\nApple EBITDA margin is 999999% for FY2025.\n"
        self.assertTrue(visible_output_integrity(run, CASE).passed)
        self.assertFalse(visible_supported_claims(run, CASE).passed)

    def test_nonfinancial_counts_and_page_numbers_are_not_checkable_claims(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = (
            "The workflow used 6 specialist nodes. See page 12 and Table 1. "
            "Apple EBITDA margin is 34.27% for FY2025 [lumenfin:sample_db:Apple:FY2025]."
        )
        result = visible_supported_claims(run, _case(require_visible_claim_citations=True))
        self.assertTrue(result.passed, [item.message for item in result.findings])

    def test_reasonable_citation_format_is_accepted(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = "Microsoft EBITDA margin is 42.45% for FY2025 [sample_notes.md#p1]."
        result = visible_supported_claims(run, CASE)
        self.assertTrue(result.passed, [item.message for item in result.findings])

    def test_percent_hundredfold_and_currency_scale_are_blocked(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = BASELINE["final_output"].replace(
            "Apple EBITDA margin is 34.27% for FY2025",
            "Apple EBITDA margin is 0.342718% for FY2025",
        )
        self.assertFalse(visible_supported_claims(run, CASE).passed)
        money = dict(BASELINE)
        money["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412.0 million USD")
        self.assertFalse(visible_supported_claims(money, CASE).passed)
        fx = dict(BASELINE)
        fx["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412.0 billion EUR")
        self.assertFalse(visible_supported_claims(fx, CASE).passed)

    def test_same_entity_unrelated_page_is_not_numeric_support(self) -> None:
        run = dict(BASELINE)
        run["evidence"] = list(BASELINE["evidence"]) + [
            {
                "entity": "Apple",
                "citation": "risk.md#p9",
                "period": "FY2025",
                "source_type": "document",
                "text": "Apple FY2025 supply-chain concentration remains elevated in one assembly region.",
            }
        ]
        run["final_output"] = BASELINE["final_output"].replace(
            "Apple FY2025 revenue was 412.0 billion USD [lumenfin:sample_db:Apple:FY2025].",
            "Apple FY2025 revenue was 412.0 billion USD [risk.md#p9].",
        )
        result = visible_supported_claims(run, CASE)
        self.assertFalse(result.passed)
        self.assertTrue(any("wrong_citation" in str(item.target) for item in result.findings))

    def test_same_entity_wrong_metric_page_is_not_revenue_support(self) -> None:
        run = dict(BASELINE)
        run["evidence"] = list(BASELINE["evidence"]) + [
            {
                "entity": "Apple",
                "citation": "rd.md#p2",
                "period": "FY2025",
                "source_type": "document",
                "text": "Apple FY2025 research and development was 31.3 billion USD.",
            }
        ]
        run["final_output"] = BASELINE["final_output"].replace(
            "Apple FY2025 revenue was 412.0 billion USD [lumenfin:sample_db:Apple:FY2025].",
            "Apple FY2025 revenue was 412.0 billion USD [rd.md#p2].",
        )
        self.assertFalse(visible_supported_claims(run, CASE).passed)

    def test_local_currency_window_rejects_eur_cny_and_unknown_iso(self) -> None:
        buried = dict(BASELINE)
        buried["final_output"] = BASELINE["final_output"].replace(
            "412.0 billion USD",
            "412.0 billion EUR (figures are not USD)",
        )
        self.assertFalse(visible_supported_claims(buried, CASE).passed)
        cny = dict(BASELINE)
        cny["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412.0 billion CNY")
        self.assertFalse(visible_supported_claims(cny, CASE).passed)
        xyz = dict(BASELINE)
        xyz["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412.0 billion XYZ")
        self.assertFalse(visible_supported_claims(xyz, CASE).passed)

    def test_ratio_unit_does_not_guess_percent_scale(self) -> None:
        run = {
            "schema_version": "1.0",
            "run_id": "ratio-unit",
            "query": "ratio",
            "entities": [{"name": "Apple"}],
            "metrics": [
                {
                    "entity": "Apple",
                    "name": "ebitda_margin",
                    "period": "FY2025",
                    "value": 2.0,
                    "unit": "ratio",
                    "formula": "ebitda / revenue",
                    "inputs": {
                        "ebitda": {
                            "value": 200.0,
                            "unit": "billion",
                            "currency": "USD",
                            "period": "FY2025",
                            "evidence_ids": ["ev_r_ebitda"],
                        },
                        "revenue": {
                            "value": 100.0,
                            "unit": "billion",
                            "currency": "USD",
                            "period": "FY2025",
                            "evidence_ids": ["ev_r_rev"],
                        },
                    },
                }
            ],
            "evidence": [
                {
                    "id": "ev_r_rev",
                    "entity": "Apple",
                    "metric": "revenue",
                    "value": 100.0,
                    "unit": "billion",
                    "currency": "USD",
                    "citation": "lumenfin:sample_db:Apple:FY2025",
                    "period": "FY2025",
                    "text": "structured",
                },
                {
                    "id": "ev_r_ebitda",
                    "entity": "Apple",
                    "metric": "ebitda",
                    "value": 200.0,
                    "unit": "billion",
                    "currency": "USD",
                    "citation": "lumenfin:sample_db:Apple:FY2025",
                    "period": "FY2025",
                    "text": "structured",
                },
            ],
            "claims": [],
            "final_output": "Apple EBITDA margin is 2% for FY2025 [lumenfin:sample_db:Apple:FY2025].",
        }
        self.assertFalse(visible_supported_claims(run, CASE).passed)
        run["final_output"] = "Apple EBITDA margin is 200% for FY2025 [lumenfin:sample_db:Apple:FY2025]."
        self.assertTrue(visible_supported_claims(run, CASE).passed)
        small = dict(run)
        small["metrics"] = [{**run["metrics"][0], "value": 0.012}]
        small["final_output"] = "Apple EBITDA margin is 1.2% for FY2025 [lumenfin:sample_db:Apple:FY2025]."
        self.assertTrue(visible_supported_claims(small, CASE).passed)
        small["final_output"] = "Apple EBITDA margin is 0.012% for FY2025 [lumenfin:sample_db:Apple:FY2025]."
        self.assertFalse(visible_supported_claims(small, CASE).passed)

    def test_parser_binds_complete_amount_currency_and_scale(self) -> None:
        from finagentbench.metrics.visible_supported_claims import parse_visible_assertions

        rows = [
            ("Apple revenue was 412.0 billion USD for FY2025.", 412.0, "USD", 1e9, False),
            ("Apple revenue was 412000 billion USD for FY2025.", 412000.0, "USD", 1e9, False),
            ("Apple revenue was 412,000 million USD for FY2025.", 412000.0, "USD", 1e6, False),
            ("Apple revenue was EUR 412.0 billion for FY2025.", 412.0, "EUR", 1e9, False),
            ("Apple revenue was $412.0 billion for FY2025.", 412.0, "USD", 1e9, False),
            ("Apple EBITDA margin is 200% for FY2025.", 200.0, "", None, True),
        ]
        for text, value, currency, scale, percent in rows:
            assertions = parse_visible_assertions(text, ["Apple"])
            self.assertTrue(assertions, text)
            amount = assertions[0].amount
            self.assertFalse(amount.unparsed, text)
            self.assertEqual(amount.value, value, text)
            self.assertEqual(amount.currency, currency, text)
            self.assertEqual(amount.scale, scale, text)
            self.assertEqual(amount.percent, percent, text)
        sci = parse_visible_assertions("Apple revenue was 4.12e2 billion USD for FY2025.", ["Apple"])
        self.assertTrue(assertions := sci)
        self.assertTrue(assertions[0].amount.unparsed)

    def test_contradictory_evidence_value_is_not_support(self) -> None:
        run = dict(BASELINE)
        run["evidence"] = [
            {
                **dict(BASELINE["evidence"][0]),
                "value": 1.0,
                "text": "Apple FY2025 revenue was 1.0 billion USD.",
            },
            *list(BASELINE["evidence"][1:]),
        ]
        self.assertFalse(visible_supported_claims(run, CASE).passed)
        huge = dict(BASELINE)
        huge["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412000 billion USD")
        self.assertFalse(visible_supported_claims(huge, CASE).passed)
        prefix = dict(BASELINE)
        prefix["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "EUR 412.0 billion")
        self.assertFalse(visible_supported_claims(prefix, CASE).passed)
        comma = dict(BASELINE)
        comma["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "412,000 million USD")
        self.assertTrue(visible_supported_claims(comma, CASE).passed)
        sci = dict(BASELINE)
        sci["final_output"] = BASELINE["final_output"].replace("412.0 billion USD", "4.12e2 billion USD")
        self.assertFalse(visible_supported_claims(sci, CASE).passed)

    def test_undisclosed_page_is_not_financial_support(self) -> None:
        run = dict(BASELINE)
        run["evidence"] = list(BASELINE["evidence"]) + [
            {
                "id": "ev_missing",
                "entity": "Apple",
                "citation": "missing.md#p9",
                "period": "FY2025",
                "source_type": "document",
                "text": "Apple FY2025 EBITDA and revenue are not disclosed in this document.",
            }
        ]
        run["final_output"] = BASELINE["final_output"].replace(
            "[lumenfin:sample_db:Apple:FY2025]",
            "[missing.md#p9]",
        )
        self.assertFalse(visible_supported_claims(run, CASE).passed)

    def test_multi_source_ratio_inputs_pass(self) -> None:
        run = dict(BASELINE)
        run["evidence"] = [
            {
                "id": "ev_apple_revenue_fy2025",
                "entity": "Apple",
                "metric": "revenue",
                "value": 412.0,
                "unit": "billion",
                "currency": "USD",
                "citation": "10k.pdf#p1",
                "period": "FY2025",
                "text": "structured revenue",
            },
            {
                "id": "ev_apple_ebitda_fy2025",
                "entity": "Apple",
                "metric": "ebitda",
                "value": 141.2,
                "unit": "billion",
                "currency": "USD",
                "citation": "notes.md#p2",
                "period": "FY2025",
                "text": "structured ebitda",
            },
            {
                "id": "ev_msft_revenue_fy2025",
                "entity": "Microsoft",
                "metric": "revenue",
                "value": 288.7,
                "unit": "billion",
                "currency": "USD",
                "citation": "sample_notes.md#p1",
                "period": "FY2025",
                "text": "msft rev",
            },
            {
                "id": "ev_msft_ebitda_fy2025",
                "entity": "Microsoft",
                "metric": "ebitda",
                "value": 122.5,
                "unit": "billion",
                "currency": "USD",
                "citation": "sample_notes.md#p1",
                "period": "FY2025",
                "text": "msft ebitda",
            },
        ]
        metrics = list(BASELINE["metrics"])
        apple = dict(metrics[0])
        apple["inputs"] = {
            "ebitda": {**metrics[0]["inputs"]["ebitda"], "evidence_ids": ["ev_apple_ebitda_fy2025"]},
            "revenue": {**metrics[0]["inputs"]["revenue"], "evidence_ids": ["ev_apple_revenue_fy2025"]},
        }
        run["metrics"] = [apple, metrics[1]]
        run["final_output"] = (
            "Apple EBITDA margin is 34.27% for FY2025 [10k.pdf#p1] [notes.md#p2]. "
            "Microsoft EBITDA margin is 42.45% for FY2025 [sample_notes.md#p1]. "
            "Apple FY2025 revenue was 412.0 billion USD [10k.pdf#p1]."
        )
        result = visible_supported_claims(run, CASE)
        self.assertTrue(result.passed, [item.message for item in result.findings])

    def test_citation_must_belong_to_the_asserted_entity(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = BASELINE["final_output"].replace(
            "[lumenfin:sample_db:Apple:FY2025]",
            "[sample_notes.md#p1]",
            1,
        )
        result = visible_supported_claims(run, CASE)
        self.assertFalse(result.passed)
        self.assertTrue(any("wrong_citation" in str(item.target) for item in result.findings))

    def test_evidence_unit_currency_and_null_value_are_verified(self) -> None:
        run = copy_baseline = dict(BASELINE)
        del copy_baseline
        fx = dict(BASELINE)
        evidence = [dict(item) for item in BASELINE["evidence"]]
        evidence[0] = dict(evidence[0], currency="EUR")
        fx["evidence"] = evidence
        self.assertFalse(visible_supported_claims(fx, CASE).passed)
        scale = dict(BASELINE)
        evidence = [dict(item) for item in BASELINE["evidence"]]
        evidence[0] = dict(evidence[0], unit="million")
        scale["evidence"] = evidence
        self.assertFalse(visible_supported_claims(scale, CASE).passed)
        missing = dict(BASELINE)
        evidence = [dict(item) for item in BASELINE["evidence"]]
        evidence[0] = dict(evidence[0], value=None)
        missing["evidence"] = evidence
        self.assertFalse(visible_supported_claims(missing, CASE).passed)
        equiv = dict(BASELINE)
        evidence = [dict(item) for item in BASELINE["evidence"]]
        evidence[0] = dict(evidence[0], value=412000.0, unit="million", currency="USD")
        equiv["evidence"] = evidence
        self.assertTrue(visible_supported_claims(equiv, CASE).passed)

    def test_markdown_table_cells_are_checked(self) -> None:
        table = (
            "\n| Company | FY2025 EBITDA margin |\n"
            "|---|---|\n"
            "| Apple | 34.27% [lumenfin:sample_db:Apple:FY2025] |\n"
        )
        ok = dict(BASELINE)
        ok["final_output"] = BASELINE["final_output"] + table
        self.assertTrue(visible_supported_claims(ok, CASE).passed)
        bad = dict(BASELINE)
        bad["final_output"] = BASELINE["final_output"] + table.replace("34.27%", "99.9%")
        result = visible_supported_claims(bad, CASE)
        self.assertFalse(result.passed)
        self.assertTrue(any(item.target.get("origin") == "table" for item in result.findings))
        wide = dict(BASELINE)
        wide["final_output"] = (
            BASELINE["final_output"]
            + "\n| Metric | Apple | Microsoft |\n|---|---|---|\n"
            + "| EBITDA margin | 34.27% [lumenfin:sample_db:Apple:FY2025] | 42.45% [sample_notes.md#p1] |\n"
        )
        self.assertTrue(visible_supported_claims(wide, CASE).passed, "wide company columns")
        unparsed = dict(BASELINE)
        unparsed["final_output"] = BASELINE["final_output"] + (
            "\n| ColA | ColB |\n|---|---|\n| 99.9% | 12 billion USD |\n"
        )
        self.assertFalse(visible_supported_claims(unparsed, CASE).passed)

    def test_claim_ledger_rows_are_scored_and_catalogs_are_not(self) -> None:
        cite = "[lumenfin:sample_db:Apple:FY2025]"
        ledger = (
            "\n| Entity | Type | Statement | Source |\n|---|---|---|---|\n"
            f"| Apple | Claim | Apple EBITDA margin is 34.27% for FY2025. | {cite} |\n"
        )
        good = dict(BASELINE)
        good["final_output"] = BASELINE["final_output"] + ledger
        self.assertTrue(visible_supported_claims(good, CASE).passed, "correct ledger")

        wrong_number = dict(BASELINE)
        wrong_number["final_output"] = BASELINE["final_output"] + ledger.replace("34.27%", "99.9%")
        number_result = visible_supported_claims(wrong_number, CASE)
        self.assertFalse(number_result.passed)
        self.assertTrue(any(item.target.get("code") == "wrong_number" for item in number_result.findings))

        wrong_source = dict(BASELINE)
        wrong_source["final_output"] = BASELINE["final_output"] + ledger.replace(
            "lumenfin:sample_db:Apple:FY2025", "forged.md#p99"
        )
        source_result = visible_supported_claims(wrong_source, CASE)
        self.assertFalse(source_result.passed)
        self.assertTrue(any(item.target.get("code") == "wrong_citation" for item in source_result.findings))

        contradiction = dict(BASELINE)
        contradiction["final_output"] = BASELINE["final_output"] + (
            "\n| Entity | Statement | Source |\n|---|---|---|\n"
            f"| Apple | Apple EBITDA margin is 99.9% for FY2025. | {cite} |\n"
        )
        self.assertFalse(visible_supported_claims(contradiction, CASE).passed)

        catalog = dict(BASELINE)
        catalog["final_output"] = BASELINE["final_output"] + (
            "\n| Company | Citation | Method | Excerpt |\n|---------|----------|--------|---------|\n"
            "| NVIDIA | notes.md p.1 | hybrid | used 6 specialist nodes; DER 81,453 |\n"
        )
        catalog_result = visible_supported_claims(catalog, CASE)
        self.assertTrue(catalog_result.passed, [item.message for item in catalog_result.findings])

    def test_iso_timestamp_is_not_a_fiscal_year_and_evidence_catalog_is_ignored(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = (
            BASELINE["final_output"]
            + "\nLive market snapshot [lumenfin:market_snapshot:NVIDIA:2026-09-08T03:10:18+00:00].\n"
            + "| Company | Citation | Method | Excerpt |\n|---------|----------|--------|---------|\n"
            + "| NVIDIA | nvda.pdf p.1 | hybrid | DER 81,453 operating income |\n"
        )
        result = visible_supported_claims(run, CASE)
        self.assertTrue(result.passed, [item.message for item in result.findings])

    def test_unverifiable_prose_is_not_treated_as_verified(self) -> None:
        run = dict(BASELINE)
        run["final_output"] = "Management commentary remained cautious about supply concentration."
        result = visible_supported_claims(
            run, _case(require_checkable_metrics=False, require_visible_claim_citations=False)
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.findings, [])

    def test_stated_period_is_checked_against_dated_fact_not_empty_or_cover_year(self) -> None:
        run = {
            "schema_version": BASELINE["schema_version"],
            "run_id": "period-bind",
            "final_output": (
                "NVIDIA Operating income is 32.97 billion USD for FY2025 [annual.pdf#p2]."
            ),
            "entities": [{"name": "NVIDIA"}],
            "metrics": [
                {
                    "entity": "NVIDIA",
                    "name": "operating_income",
                    "value": 32.972,
                    "unit": "billion",
                    "period": "latest",
                    "currency": "USD",
                },
                {
                    "entity": "NVIDIA",
                    "name": "operating_income",
                    "value": 32.972,
                    "unit": "billion",
                    "period": "FY2024",
                    "currency": "USD",
                    "citation": "annual.pdf#p2",
                },
            ],
            "evidence": [
                {
                    "id": "ev_oi",
                    "entity": "NVIDIA",
                    "metric": "operating_income",
                    "value": 32.972,
                    "unit": "billion",
                    "currency": "USD",
                    "period": "FY2024",
                    "citation": "annual.pdf#p2",
                }
            ],
            "steps": [],
            "claims": [],
        }
        result = visible_supported_claims(
            run,
            _case(require_visible_claim_citations=False, require_checkable_metrics=True),
        )
        self.assertFalse(result.passed, [item.message for item in result.findings])
        self.assertTrue(any("wrong_period" in str(item.target) or "FY2024" in item.message for item in result.findings))

    def test_unknown_or_latest_fact_cannot_support_a_specific_year(self) -> None:
        cite = "annual.pdf#p2"
        run = {
            "schema_version": BASELINE["schema_version"],
            "run_id": "unknown-period",
            "final_output": f"NVIDIA operating income is 32.972 billion USD for FY2025 [{cite}].",
            "entities": [{"name": "NVIDIA"}],
            "metrics": [
                {
                    "entity": "NVIDIA",
                    "name": "operating_income",
                    "value": 32.972,
                    "unit": "billion",
                    "period": "unknown",
                    "currency": "USD",
                    "citation": cite,
                }
            ],
            "evidence": [
                {
                    "id": "ev_oi_unknown",
                    "entity": "NVIDIA",
                    "metric": "operating_income",
                    "value": 32.972,
                    "unit": "billion",
                    "currency": "USD",
                    "period": "unknown",
                    "citation": cite,
                }
            ],
            "steps": [],
            "claims": [],
        }
        result = visible_supported_claims(run, _case(require_visible_claim_citations=True))
        self.assertFalse(result.passed, [item.message for item in result.findings])
        self.assertTrue(
            any(isinstance(item.target, dict) and item.target.get("code") == "wrong_period" for item in result.findings),
            [item.target for item in result.findings],
        )
        honest = dict(run)
        honest["final_output"] = (
            f"NVIDIA operating income is 32.972 billion USD (period not stated in the source) [{cite}]."
        )
        honest_result = visible_supported_claims(honest, _case(require_visible_claim_citations=True))
        self.assertTrue(honest_result.passed, [item.message for item in honest_result.findings])

    def test_product_quality_mutation_suite_detects_visible_only_faults(self) -> None:
        report = run_benchmark_suite(ROOT / "benchmarks" / "mutations" / "product_quality_visible_v1.json")
        self.assertTrue(report["passed"], json.dumps(report["items"], indent=2)[:4000])
        self.assertEqual(report["false_positives"], 0)
        self.assertEqual(report["detected_failures"], report["expected_failures"])


if __name__ == "__main__":
    unittest.main()
