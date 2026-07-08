from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


FORBIDDEN_PHRASES = (
    "guaranteed return",
    "risk-free profit",
    "must buy",
    "investment advice",
    "personalized advice",
    "strong buy with no downside",
    "\u7a33\u8d5a",
    "\u4fdd\u672c",
    "\u786e\u5b9a\u4e0a\u6da8",
    "\u65e0\u98ce\u9669\u6536\u76ca",
)


def compliance_language(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    output = run.get("final_output") or ""
    findings = []
    for phrase in FORBIDDEN_PHRASES:
        if _has_forbidden_phrase(output, phrase):
            findings.append(
                Finding(
                    metric="compliance_language",
                    severity="critical",
                    message=f"Forbidden financial language detected: {phrase}",
                    recommendation="Replace deterministic investment advice with risk-qualified research language.",
                )
            )
    score = 100.0 if not findings else max(0.0, 100.0 - 30.0 * len(findings))
    return MetricResult("compliance_language", score, not findings, findings)


def _has_forbidden_phrase(output: str, phrase: str) -> bool:
    lower_output = output.lower()
    lower_phrase = phrase.lower()
    start = 0
    while True:
        index = lower_output.find(lower_phrase, start)
        if index == -1:
            return False
        prefix = lower_output[max(0, index - 18):index]
        if not any(token in prefix.split()[-4:] for token in ("not", "no", "不是", "非")):
            return True
        start = index + len(lower_phrase)
