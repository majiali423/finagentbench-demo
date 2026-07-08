from __future__ import annotations

from typing import Any

from ..schema import Finding, MetricResult


def section_presence(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    required = case.get("required_sections", [])
    if not required:
        return MetricResult("section_presence", 100.0, True, [])

    output = (run.get("final_output") or "").lower()
    aliases = case.get("section_aliases", {})
    findings = []
    passed = 0
    for section in required:
        candidates = [str(section), *[str(alias) for alias in aliases.get(section, [])]]
        if any(candidate.lower() in output for candidate in candidates):
            passed += 1
            continue
        findings.append(
            Finding(
                metric="section_presence",
                severity="medium",
                message=f"Missing required report section: {section}",
                recommendation="Add the required section heading or a configured alias to the final report.",
            )
        )
    score = round(passed / len(required) * 100, 2)
    return MetricResult("section_presence", score, not findings, findings)
