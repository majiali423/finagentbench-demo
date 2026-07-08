from __future__ import annotations

import json
import unittest
from pathlib import Path

from finagentbench.adapters import load_run_file, normalize_run


ROOT = Path(__file__).resolve().parents[1]


class AdapterTestCase(unittest.TestCase):
    def test_generic_adapter_keeps_finrun_shape(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "pass_finrun.json")
        self.assertEqual(run["run_id"], "pass-nvidia-amd")
        self.assertIn("final_output", run)

    def test_lumenfin_adapter_maps_state_to_finrun(self) -> None:
        run = load_run_file(ROOT / "fixtures" / "lumenfin_state_sample.json", "lumenfin")
        self.assertEqual(run["run_id"], "lumenfin-sample-001")
        self.assertEqual({entity["name"] for entity in run["entities"]}, {"NVIDIA", "AMD"})
        self.assertTrue(any(step["name"] == "retrieval" for step in run["steps"]))
        self.assertTrue(any(metric["name"] == "r_and_d_intensity" for metric in run["metrics"]))

    def test_unknown_adapter_is_rejected(self) -> None:
        payload = json.loads((ROOT / "fixtures" / "pass_finrun.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            normalize_run(payload, "missing")


if __name__ == "__main__":
    unittest.main()
