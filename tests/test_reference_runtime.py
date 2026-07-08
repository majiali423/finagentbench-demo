from __future__ import annotations

import unittest

from finagentbench.reference_runtime import run_reference_agent
from finagentbench.runner import evaluate_run


BIGTECH_CASE = {
    "expected_entities": ["AAPL", "MSFT", "NVDA"],
    "required_steps": ["retrieval", "quant", "risk", "synthesis", "compliance"],
    "numeric_tolerance": 0.001,
    "require_temporal_consistency": True,
    "require_unit_currency_consistency": True,
    "require_risk_disclosure": True,
    "min_score": 85,
}


class ReferenceRuntimeTestCase(unittest.TestCase):
    def test_reference_agent_exports_passing_finrun(self) -> None:
        run = run_reference_agent()
        report = evaluate_run(run, BIGTECH_CASE)
        self.assertTrue(report.passed)
        self.assertEqual(report.score, 100.0)

    def test_reference_agent_records_tool_retry_and_cache_stats(self) -> None:
        run = run_reference_agent()
        tool_events = run["metadata"]["tool_events"]
        market_events = [event for event in tool_events if event["tool"] == "market_data"]
        self.assertTrue(any(event["entity"] == "NVDA" and event["attempts"] == 2 for event in market_events))
        self.assertGreater(run["metadata"]["cache"]["misses"], 0)


if __name__ == "__main__":
    unittest.main()
