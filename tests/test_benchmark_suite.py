from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from finagentbench.benchmark import (
    run_benchmark_suite,
    run_live_semantic_benchmark_suite,
    run_semantic_benchmark_suite,
)


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkSuiteTestCase(unittest.TestCase):
    def test_due_diligence_suite_detects_curated_failures(self) -> None:
        payload = run_benchmark_suite(ROOT / "benchmarks" / "due_diligence" / "suite.json")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total_traces"], 10)
        self.assertEqual(payload["expected_failures"], 9)
        self.assertEqual(payload["detected_failures"], 9)
        self.assertEqual(payload["detection_rate"], 1.0)
        self.assertGreaterEqual(payload["covered_failure_type_count"], 8)

    def test_semantic_golden_suite_matches_human_labels(self) -> None:
        payload = run_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "evidence_support_golden.json"
        )
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total"], 20)
        self.assertEqual(payload["matched"], 20)
        self.assertEqual(payload["benchmark_mode"], "static_judge_replay")
        self.assertEqual(payload["measures"], "pipeline_replay_consistency_not_live_llm_accuracy")
        self.assertEqual(payload["replay_match_rate"], 1.0)
        self.assertEqual(payload["false_positives"], 0)
        self.assertEqual(payload["false_negatives"], 0)
        self.assertGreaterEqual(len(payload["by_failure_type"]), 10)

    def test_risk_quality_golden_suite_matches_human_labels(self) -> None:
        payload = run_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "risk_quality_golden.json"
        )
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["metric"], "risk_quality")
        self.assertEqual(payload["total"], 10)
        self.assertEqual(payload["matched"], 10)
        self.assertEqual(payload["false_positives"], 0)
        self.assertEqual(payload["false_negatives"], 0)

    def test_compliance_semantic_golden_suite_matches_human_labels(self) -> None:
        payload = run_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "compliance_semantic_golden.json"
        )
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["metric"], "compliance_semantic")
        self.assertEqual(payload["total"], 10)
        self.assertEqual(payload["matched"], 10)
        self.assertEqual(payload["false_positives"], 0)
        self.assertEqual(payload["false_negatives"], 0)

    def test_lumenfin_regression_suite_catches_before_after_failures(self) -> None:
        payload = run_benchmark_suite(ROOT / "benchmarks" / "lumenfin_regression" / "suite.json")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["total_traces"], 3)
        self.assertEqual(payload["expected_failures"], 2)
        self.assertEqual(payload["detected_failures"], 2)
        items = {item["id"]: item for item in payload["items"]}
        self.assertTrue(items["lumenfin_baseline"]["actual_passed"])
        self.assertIn("numeric_correctness", items["lumenfin_wrong_quant"]["actual_findings"])
        self.assertIn("risk_disclosure", items["lumenfin_missing_risk_section"]["actual_findings"])

    def test_live_semantic_benchmark_runner_shape(self) -> None:
        """Static judge replay checks live-benchmark output fields, not live inference."""
        payload = run_live_semantic_benchmark_suite(
            ROOT / "benchmarks" / "semantic_audit" / "evidence_support_golden.json",
            {
                "provider": "static",
                "results": {
                    "evidence_support": {
                        "score": 91,
                        "passed": True,
                        "rationale": "The claim is supported.",
                        "severity": "low",
                        "labels": ["supported"],
                    }
                },
            },
            limit=1,
        )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["benchmark_mode"], "live_llm_judge_small_sample")
        self.assertEqual(
            payload["measures"],
            "live_judge_alignment_with_human_labels_not_production_accuracy",
        )
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["matched"], 1)
        self.assertEqual(payload["items"][0]["judge"]["provider"], "static")

    def test_live_semantic_benchmark_uses_openai_compatible_http_judge(self) -> None:
        handler = _semantic_handler()
        server = HTTPServer(("127.0.0.1", 0), handler)
        server.request_count = 0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with TemporaryDirectory() as tmp:
                payload = run_live_semantic_benchmark_suite(
                    ROOT / "benchmarks" / "semantic_audit" / "evidence_support_golden.json",
                    {
                        "provider": "openai-compatible",
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                        "api_key": "test-key",
                        "model": "mock-finance-judge",
                        "prompt_version": "evidence_support_http_test_v1",
                        "cache_path": str(Path(tmp) / "judge-cache.json"),
                        "retry_count": 0,
                        "backoff_seconds": 0,
                    },
                    limit=1,
                )

                self.assertTrue(payload["passed"])
                self.assertEqual(payload["provider"], "openai-compatible")
                self.assertEqual(payload["model"], "mock-finance-judge")
                self.assertEqual(payload["prompt_version"], "evidence_support_http_test_v1")
                self.assertEqual(payload["matched"], 1)
                self.assertEqual(server.request_count, 1)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


def _semantic_handler():
    class SemanticHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.server.request_count += 1
            length = int(self.headers.get("content-length", "0"))
            self.rfile.read(length)
            response_payload = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "score": 91,
                                    "passed": True,
                                    "rationale": "The first golden item is supported by cited evidence.",
                                    "severity": "low",
                                    "labels": ["supported_summary"],
                                }
                            )
                        }
                    }
                ]
            }
            body = json.dumps(response_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return SemanticHandler


if __name__ == "__main__":
    unittest.main()
