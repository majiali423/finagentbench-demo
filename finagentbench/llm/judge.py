from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class JudgeResult:
    score: float
    passed: bool
    rationale: str
    severity: str = "medium"
    labels: list[str] = field(default_factory=list)


class SemanticJudge(Protocol):
    def judge(self, task: str, payload: dict[str, Any]) -> JudgeResult:
        """Return a structured semantic audit result for one task."""


class StaticJudge:
    """Offline judge for tests, demos, and golden-label replay."""

    def __init__(self, results: dict[str, Any]) -> None:
        self._results = results

    def judge(self, task: str, payload: dict[str, Any]) -> JudgeResult:
        del payload
        result = self._results.get(task, self._results.get("default", {}))
        return _parse_result(result)


class RuleJudge:
    """Deterministic fallback used when no external LLM is configured."""

    def judge(self, task: str, payload: dict[str, Any]) -> JudgeResult:
        if task != "evidence_support":
            return JudgeResult(100.0, True, "No rule-based check configured for this task.")

        final_output = str(payload.get("final_output", "")).lower()
        evidence_text = " ".join(str(item.get("text", "")) for item in payload.get("evidence", [])).lower()
        missing_entities = [
            entity for entity in payload.get("entities", [])
            if str(entity).lower() not in final_output or str(entity).lower() not in evidence_text
        ]
        if missing_entities:
            return JudgeResult(
                score=60.0,
                passed=False,
                rationale=f"Entities are not consistently present in both answer and evidence: {missing_entities}",
                severity="high",
                labels=["entity_support_gap"],
            )
        return JudgeResult(
            score=85.0,
            passed=True,
            rationale="Rule fallback found entity overlap between answer and cited evidence.",
            labels=["rule_fallback"],
        )


class OpenAICompatibleJudge:
    """Small HTTP adapter for OpenAI-compatible chat-completion endpoints.

    The endpoint is intentionally configured through environment variables so
    the benchmark remains dependency-free and provider-neutral by default.
    """

    def __init__(self, endpoint: str, api_key: str, model: str, timeout_seconds: float = 20.0) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def judge(self, task: str, payload: dict[str, Any]) -> JudgeResult:
        request_payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial-agent audit judge. Return only JSON with "
                        "score, passed, rationale, severity, and labels."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"task": task, "payload": payload}, ensure_ascii=False),
                },
            ],
        }
        body = json.dumps(request_payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return JudgeResult(
                score=0.0,
                passed=False,
                rationale=f"Semantic judge request failed: {exc}",
                severity="medium",
                labels=["judge_unavailable"],
            )

        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            return _parse_result(json.loads(content))
        except json.JSONDecodeError:
            return JudgeResult(
                score=0.0,
                passed=False,
                rationale="Semantic judge returned non-JSON content.",
                severity="medium",
                labels=["judge_bad_response"],
            )


def build_judge(config: dict[str, Any] | None = None) -> SemanticJudge:
    config = config or {}
    provider = str(config.get("provider", "rule")).lower()
    if provider == "static":
        return StaticJudge(config.get("results", {}))
    if provider in {"openai-compatible", "openai_compatible"}:
        endpoint = str(config.get("endpoint") or os.getenv("FINAGENTBENCH_LLM_ENDPOINT", ""))
        api_key = str(config.get("api_key") or os.getenv("FINAGENTBENCH_LLM_API_KEY", ""))
        model = str(config.get("model") or os.getenv("FINAGENTBENCH_LLM_MODEL", ""))
        if not endpoint or not api_key or not model:
            return StaticJudge(
                {
                    "default": {
                        "score": 0,
                        "passed": False,
                        "rationale": "OpenAI-compatible judge is missing endpoint, api key, or model configuration.",
                        "severity": "medium",
                        "labels": ["judge_not_configured"],
                    }
                }
            )
        return OpenAICompatibleJudge(endpoint, api_key, model, float(config.get("timeout_seconds", 20)))
    return RuleJudge()


def _parse_result(result: dict[str, Any]) -> JudgeResult:
    score = float(result.get("score", 0.0))
    return JudgeResult(
        score=max(0.0, min(100.0, score)),
        passed=bool(result.get("passed", score >= 80.0)),
        rationale=str(result.get("rationale", "")),
        severity=str(result.get("severity", "medium")),
        labels=[str(label) for label in result.get("labels", [])],
    )
