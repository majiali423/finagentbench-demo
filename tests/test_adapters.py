from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finagentbench.adapters import load_run_file, normalize_run
from finagentbench.adapters.compare import comparable_finrun
from finagentbench.schema import validate_finrun


ROOT = Path(__file__).resolve().parents[1]


class AdapterTestCase(unittest.TestCase):
    def test_generic_adapter_keeps_finrun_shape(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "pass_finrun.json")
        self.assertEqual(run["run_id"], "pass-nvidia-amd")
        self.assertIn("final_output", run)

    def test_agent_state_adapter_maps_state_to_finrun(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "agent_state_sample.json", "agent-state")
        self.assertEqual(run["run_id"], "agent-state-sample-001")
        self.assertEqual({entity["name"] for entity in run["entities"]}, {"NVIDIA", "AMD"})
        self.assertTrue(any(step["name"] == "retrieval" for step in run["steps"]))
        self.assertTrue(any(metric["name"] == "r_and_d_intensity" for metric in run["metrics"]))

    def test_lumenfin_adapter_maps_state_to_finrun(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        self.assertEqual(run["run_id"], "lumenfin-e2e-apple-microsoft")
        self.assertEqual({entity["name"] for entity in run["entities"]}, {"Apple", "Microsoft"})
        self.assertTrue(any(step["name"] == "quant" for step in run["steps"]))
        self.assertTrue(any(metric["name"] == "ebitda_margin" and metric["formula"] for metric in run["metrics"]))
        self.assertTrue(any(item["source_type"] == "sample_db" for item in run["evidence"]))
        validate_finrun(run)
        self.assertIn("claims", run)

    def test_lumenfin_and_generic_finrun_views_are_schema_compatible(self) -> None:
        lumen = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        generic = load_run_file(ROOT / "fixtures" / "pass_finrun.json", "generic")
        validate_finrun(lumen)
        validate_finrun(generic)
        self.assertEqual(set(comparable_finrun(lumen)), set(comparable_finrun(generic)))

    def test_agent_state_adapter_emits_valid_finrun_shape(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "agent_state_sample.json", "agent-state")
        validate_finrun(run)

    def test_lumenfin_adapter_is_auto_detected_before_generic_agent_state(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json")
        self.assertEqual(run["metadata"]["adapter"], "lumenfin")
        self.assertTrue(run["metrics"])

    def test_unknown_adapter_is_rejected(self) -> None:
        payload = json.loads((ROOT / "fixtures" / "pass_finrun.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            normalize_run(payload, "missing")


if __name__ == "__main__":
    unittest.main()
