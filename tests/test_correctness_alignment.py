"""Correctness tests for FinAgentBench ↔ LumenFin FinRun alignment."""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file
from finagentbench.adapters.lumenfin import LumenFinAdapter, get_fundamental
from finagentbench.metrics.entity import entity_leakage
from finagentbench.metrics.sections import section_presence
from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]
LUMEN = Path(os.getenv("LUMENFIN_ROOT", ROOT.parent / "lumenfin-agent")).resolve()


def _load_case(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class CanonicalFinRunAlignmentTestCase(unittest.TestCase):
    def test_get_fundamental_accepts_canonical_and_legacy(self) -> None:
        self.assertEqual(get_fundamental({"revenue": 416.1}, "revenue"), 416.1)
        self.assertEqual(get_fundamental({"revenue_2025": 412.0}, "revenue"), 412.0)

    def test_sample_fixture_still_has_checkable_inputs(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        checkable = [m for m in run["metrics"] if m.get("formula") and m.get("inputs")]
        self.assertGreaterEqual(len(checkable), 2)
        for metric in checkable:
            self.assertIn("period", metric)
            self.assertTrue(metric.get("source") or metric.get("confidence"))

    def test_live_apple_state_has_checkable_inputs(self) -> None:
        matches = sorted(LUMEN.glob("outputs/e2e-ag01_apple_live-*_state.json"))
        if not matches:
            self.skipTest("no live Apple state")
        state = json.loads(matches[-1].read_text(encoding="utf-8"))
        run = LumenFinAdapter().normalize(state)
        checkable = [m for m in run["metrics"] if m.get("formula") and m.get("inputs")]
        self.assertGreaterEqual(len(checkable), 1, run["metrics"][:3])
        # No hard dependency on revenue_2025 keys in market_data.
        apple_md = ((state.get("retrieved_docs") or {}).get("Apple") or {}).get("market_data") or {}
        self.assertTrue("revenue" in apple_md or "revenue_2025" in apple_md)


class EntityLeakageTestCase(unittest.TestCase):
    def test_forbidden_peer_is_detected(self) -> None:
        run = {
            "run_id": "leak",
            "entities": [{"name": "NVIDIA"}, {"name": "AMD"}],
            "steps": [],
            "metrics": [],
            "evidence": [],
            "market_data": [],
            "final_output": "x",
        }
        case = {"forbidden_entities": ["AMD", "Intel"]}
        result = entity_leakage(run, case)
        self.assertFalse(result.passed)
        self.assertTrue(any("AMD" in f.message for f in result.findings))

    def test_compare_allows_requested_peer(self) -> None:
        run = {
            "run_id": "compare",
            "entities": [{"name": "NVIDIA"}, {"name": "AMD"}],
            "steps": [],
            "metrics": [],
            "evidence": [],
            "market_data": [],
            "final_output": "x",
        }
        case = _load_case("case_lumenfin_compare_nvda_amd.json")
        result = entity_leakage(run, case)
        self.assertTrue(result.passed)
        coverage = evaluate_run(
            {
                **run,
                "steps": [{"name": s, "status": "ok"} for s in case["required_steps"]],
                "metrics": [
                    {
                        "entity": "NVIDIA",
                        "name": "ebitda_margin",
                        "period": "FY2025",
                        "value": 0.5,
                        "formula": "ebitda / revenue",
                        "inputs": {
                            "ebitda": {"value": 50, "unit": "billion", "currency": "USD", "period": "FY2025"},
                            "revenue": {"value": 100, "unit": "billion", "currency": "USD", "period": "FY2025"},
                        },
                    }
                ],
                "evidence": [
                    {
                        "entity": "NVIDIA",
                        "citation": "x",
                        "period": "FY2025",
                        "source_type": "sample_db",
                        "provider": "t",
                        "text": "NVIDIA FY2025 revenue was 100 billion USD, EBITDA was 50 billion USD, R&D was 10 billion USD, and operating income was 40 billion USD.",
                    }
                ],
                "market_data": [{"entity": "NVIDIA", "status": "ok", "provider": "t", "as_of": "x", "error": ""}],
                "metadata": {
                    "adapter": "lumenfin",
                    "data_mode": "demo",
                    "input_guardrail_summary": {"blocked": False},
                    "retrieval_provenance": {"NVIDIA": {"structured_source": "sample_db"}, "AMD": {"structured_source": "sample_db"}},
                },
                "final_output": (
                    "## 1. Executive Summary\nok\n"
                    "## 4. Financial Performance Analysis\nok\n"
                    "## Risk\nMarket risk and data limitation remain.\n"
                    "This is research only and not investment advice.\n"
                    "## 10. Compliance Review & Data Integrity\nok\n"
                    "## 11. Methodology, Data Sources & Disclaimer\nok\n"
                ),
            },
            case,
        )
        # entity_leakage must not flag AMD when forbidden_entities is empty
        leak = next(m for m in coverage.metrics if m.name == "entity_leakage")
        self.assertTrue(leak.passed)


class SectionHeadingTestCase(unittest.TestCase):
    def test_body_keyword_does_not_count_as_section(self) -> None:
        run = {
            "final_output": (
                "# Report\n\n"
                "## 1. Executive Summary\nHello\n\n"
                "We discussed risk considerations and Risk Exposure Matrix informally in prose.\n\n"
                "## 4. Financial Performance Analysis\nNumbers\n"
            )
        }
        case = {
            "required_sections": ["## Risk"],
            "section_aliases": {
                "## Risk": ["Risk Exposure Matrix", "Risk Considerations", "Risk Architecture"]
            },
        }
        result = section_presence(run, case)
        self.assertFalse(result.passed)

    def test_markdown_heading_counts(self) -> None:
        run = {
            "final_output": (
                "## 1. Executive Summary\nx\n"
                "## Risk Exposure Matrix\nMarket risk remains.\n"
            )
        }
        case = {
            "required_sections": ["## Risk"],
            "section_aliases": {"## Risk": ["Risk Exposure Matrix"]},
        }
        result = section_presence(run, case)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
