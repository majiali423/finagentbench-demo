from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from finagentbench.llm import build_judge
from finagentbench.runner import evaluate_run


ROOT = Path(__file__).resolve().parents[1]


class SemanticAuditTestCase(unittest.TestCase):
    def test_static_judge_can_pass_evidence_support(self) -> None:
        case = _semantic_case(
            {
                "score": 92,
                "passed": True,
                "rationale": "The conclusion is supported by the cited balance-sheet evidence.",
                "severity": "low",
                "labels": ["supported"],
            }
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertTrue(metric.passed)
        self.assertEqual(metric.score, 92)

    def test_static_judge_can_fail_unsupported_claims(self) -> None:
        case = _semantic_case(
            {
                "score": 45,
                "passed": False,
                "rationale": "The conclusion adds an acquisition recommendation not present in evidence.",
                "severity": "high",
                "labels": ["unsupported_recommendation"],
            }
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertFalse(metric.passed)
        self.assertEqual(metric.findings[0].target["section"], "final_output")
        self.assertIn("unsupported_recommendation", metric.findings[0].target["labels"])
        self.assertEqual(metric.findings[0].target["judge"]["provider"], "static")

    def test_unconfigured_external_judge_degrades_to_finding(self) -> None:
        case = _load("case_due_diligence.json")
        case["enabled_metrics"] = ["evidence_support"]
        case["semantic_audit"] = {
            "judge": {"provider": "openai-compatible"},
            "min_evidence_support_score": 80,
        }
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "evidence_support")
        self.assertFalse(metric.passed)
        self.assertIn("missing endpoint", metric.findings[0].message.lower())

    def test_rule_fallback_does_not_pass_unsupported_semantic_claim(self) -> None:
        run = _load("pass_due_diligence_finrun.json")
        run["final_output"] += "\nThe buyer should acquire TargetCo immediately with guaranteed upside."
        case = _load("case_due_diligence.json")
        case["enabled_metrics"] = ["evidence_support"]
        case["semantic_audit"] = {"min_evidence_support_score": 80}

        report = evaluate_run(run, case)

        metric = _metric(report, "evidence_support")
        self.assertFalse(metric.passed)
        self.assertEqual(metric.score, 0)
        self.assertIn("semantic_judge_not_configured", metric.findings[0].target["labels"])

    def test_rule_fallback_does_not_pass_risk_or_compliance_semantic(self) -> None:
        case = _load("case_due_diligence.json")
        case["enabled_metrics"] = ["risk_quality", "compliance_semantic"]
        case["semantic_audit"] = {}

        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metrics = {metric.name: metric for metric in report.metrics}
        self.assertFalse(metrics["risk_quality"].passed)
        self.assertFalse(metrics["compliance_semantic"].passed)

    def test_static_judge_can_fail_risk_quality(self) -> None:
        case = _semantic_case(
            {
                "score": 48,
                "passed": False,
                "rationale": "Risk disclosure is generic and does not mention data-room or market risks.",
                "severity": "medium",
                "labels": ["generic_risk_language"],
            },
            metric="risk_quality",
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "risk_quality")
        self.assertFalse(metric.passed)
        self.assertIn("generic_risk_language", metric.findings[0].target["labels"])

    def test_static_judge_can_fail_compliance_semantic(self) -> None:
        case = _semantic_case(
            {
                "score": 30,
                "passed": False,
                "rationale": "The answer implies personalized acquisition advice.",
                "severity": "high",
                "labels": ["implicit_investment_advice"],
            },
            metric="compliance_semantic",
            min_score=85,
        )
        report = evaluate_run(_load("pass_due_diligence_finrun.json"), case)

        metric = _metric(report, "compliance_semantic")
        self.assertFalse(metric.passed)
        self.assertIn("implicit_investment_advice", metric.findings[0].target["labels"])

    def test_openai_compatible_judge_records_cache_and_retries(self) -> None:
        handler = _flaky_handler()
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with TemporaryDirectory() as tmp:
                cache_path = str(Path(tmp) / "judge_cache.json")
                judge = build_judge(
                    {
                        "provider": "openai-compatible",
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                        "api_key": "test-key",
                        "model": "test-model",
                        "prompt_version": "evidence_support_v2",
                        "cache_path": cache_path,
                        "retry_count": 1,
                        "backoff_seconds": 0,
                    }
                )

                first = judge.judge("evidence_support", {"final_output": "ok", "evidence": []})
                second = judge.judge("evidence_support", {"final_output": "ok", "evidence": []})

                self.assertTrue(first.passed)
                self.assertFalse(first.metadata["cached"])
                self.assertEqual(first.metadata["prompt_version"], "evidence_support_v2")
                self.assertEqual(first.metadata["model"], "test-model")
                self.assertTrue(second.passed)
                self.assertTrue(second.metadata["cached"])
                self.assertEqual(handler.call_count, 2)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


def _semantic_case(result: dict, metric: str = "evidence_support", min_score: int = 80) -> dict:
    case = _load("case_due_diligence.json")
    case["enabled_metrics"] = [metric]
    case["semantic_audit"] = {
        "judge": {
            "provider": "static",
            "prompt_version": f"{metric}_test_v1",
            "results": {metric: result},
        },
        f"min_{metric}_score": min_score,
    }
    return case


def _metric(report, name: str):
    return next(metric for metric in report.metrics if metric.name == name)


def _load(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def _flaky_handler():
    class FlakyHandler(BaseHTTPRequestHandler):
        call_count = 0

        def do_POST(self) -> None:
            type(self).call_count += 1
            if type(self).call_count == 1:
                self.send_response(500)
                self.end_headers()
                return
            length = int(self.headers.get("content-length", "0"))
            self.rfile.read(length)
            payload = {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "```json\n"
                                + json.dumps(
                                    {
                                        "score": 88,
                                        "passed": True,
                                        "rationale": "Supported by evidence.",
                                        "severity": "low",
                                        "labels": ["supported"],
                                    }
                                )
                                + "\n```"
                            )
                        }
                    }
                ]
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return FlakyHandler


if __name__ == "__main__":
    unittest.main()
