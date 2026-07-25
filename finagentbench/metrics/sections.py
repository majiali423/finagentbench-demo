from __future__ import annotations

import re
from typing import Any

from ..schema import Finding, MetricResult


_HEADING_RE = re.compile(
    r"(?m)^(#{1,6}\s+.+|[A-Z][A-Za-z0-9 &/,-]{2,80}|Part\s+[IVXLC]+\..+)$"
)


def section_presence(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    """Require section headings — not incidental keyword hits in body prose."""
    required = case.get("required_sections", [])
    if not required:
        return MetricResult("section_presence", 100.0, True, [])

    output = run.get("final_output") or ""
    headings = _extract_headings(output)
    aliases = case.get("section_aliases", {})
    findings = []
    passed = 0
    for section in required:
        candidates = [str(section), *[str(alias) for alias in aliases.get(section, [])]]
        if any(_heading_matches(candidate, headings) for candidate in candidates):
            passed += 1
            continue
        findings.append(
            Finding(
                metric="section_presence",
                severity="medium",
                message=f"Missing required report section: {section}",
                recommendation="Add the required section heading or a configured alias as a heading, not only body text.",
            )
        )
    score = round(passed / len(required) * 100, 2)
    return MetricResult("section_presence", score, not findings, findings)


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in _HEADING_RE.finditer(text or ""):
        line = match.group(1).strip()
        # Markdown headings
        if line.startswith("#"):
            line = re.sub(r"^#{1,6}\s*", "", line).strip()
        # Numbered section titles: "1. Executive Summary" / "## 4. Financial..."
        line = re.sub(r"^\d+(\.\d+)*\.\s*", "", line).strip()
        if line:
            headings.append(line)
    return headings


def _heading_matches(candidate: str, headings: list[str]) -> bool:
    needle = _normalize_heading(candidate)
    if not needle:
        return False
    # Strip leading markdown hashes from candidate if present.
    needle = re.sub(r"^#+\s*", "", needle).strip()
    for heading in headings:
        hay = _normalize_heading(heading)
        if not hay:
            continue
        if needle == hay or needle in hay or hay in needle:
            return True
    return False


def _normalize_heading(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"^\d+(\.\d+)*\.\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text
