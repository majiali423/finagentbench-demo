from __future__ import annotations

import re
from typing import Any

from ..schema import Finding, MetricResult


_REASONING_MARKERS = (
    "we need to",
    "let's draft",
    "the instruction says",
    "the user asked",
    "i need to",
    "we must",
)
_PROMPT_RESTATEMENTS = (
    "your task is",
    "the task is to",
    "the prompt asks",
    "the prompt says",
    "the instructions require",
    "i was asked to",
)
_TERMINAL_PUNCTUATION_RE = re.compile(r"[.!?。！？][\s*_~`'\"”’）)\]}]*$")
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")
_LEADERSHIP_RE = re.compile(
    r"\b(?:leads?|leading|outperforms?|trails?|lags?|ranks? (?:first|last|ahead|behind))\b",
    re.IGNORECASE,
)
_COMPANY_BEFORE_CUE_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'-]*(?:[ \t]+[A-Z][A-Za-z0-9&.'-]*){0,3})"
    r"[ \t]+(?:leads?|outperforms?|trails?|lags?|ranks?)\b"
)
_COMPANY_AFTER_CUE_RE = re.compile(
    r"\b(?:versus|vs\.?|than|against|compared (?:with|to))[ \t]+"
    r"([A-Z][A-Za-z0-9&.'-]*(?:[ \t]+[A-Z][A-Za-z0-9&.'-]*){0,3})\b"
)
_COMPANY_AFTER_LEADERSHIP_RE = re.compile(
    r"\b(?:leads?|outperforms?|trails?|lags?)[ \t]+"
    r"([A-Z][A-Za-z0-9&.'-]*(?:[ \t]+[A-Z][A-Za-z0-9&.'-]*){0,3})\b"
)


def visible_output_integrity(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    """Detect deterministic signs that user-visible output leaked or was truncated.

    Only ``final_output`` is inspected. The case is used solely to distinguish
    requested entities from unrequested companies in an explicit Peer Comparison.
    """

    output = str(run.get("final_output") or "")
    findings: list[Finding] = []

    marker = _first_phrase(output, _REASONING_MARKERS)
    if marker:
        findings.append(_finding(f"Reasoning marker leaked into final output: {marker!r}"))

    restatement = _first_phrase(output, _PROMPT_RESTATEMENTS)
    if restatement:
        findings.append(_finding(f"Prompt or task restatement leaked into final output: {restatement!r}"))

    peer_sections = _peer_sections(output)
    if any(_section_is_truncated(body) for body in peer_sections):
        findings.append(_finding("Peer Comparison section appears truncated."))

    if output.strip() and not _TERMINAL_PUNCTUATION_RE.search(output):
        findings.append(_finding("The final sentence has no ending punctuation."))

    empty_heading = _first_heading_without_prose(output)
    if empty_heading:
        findings.append(_finding(f"Markdown heading has no following prose: {empty_heading!r}"))

    entities = [_entity_name(item) for item in run.get("entities", [])]
    entities = [name for name in entities if name]
    for body in peer_sections:
        if len(entities) == 1 and _LEADERSHIP_RE.search(body):
            findings.append(
                _finding(
                    "Single-company report makes a leadership claim in Peer Comparison."
                )
            )
            break

    unknown = _first_unknown_peer(
        peer_sections,
        entities,
        [_entity_name(item) for item in case.get("forbidden_entities", [])],
    )
    if unknown:
        findings.append(
            _finding(f"Peer Comparison mentions a company outside FinRun entities: {unknown}")
        )

    return MetricResult(
        "visible_output_integrity",
        100.0 if not findings else 0.0,
        not findings,
        findings,
    )


def _first_phrase(text: str, phrases: tuple[str, ...]) -> str:
    for phrase in phrases:
        pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, phrase.split())) + r"(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return phrase
    return ""


def _peer_sections(text: str) -> list[str]:
    headings = list(_MARKDOWN_HEADING_RE.finditer(text))
    sections: list[str] = []
    for index, heading in enumerate(headings):
        title = re.sub(r"[*_`]+", "", heading.group(2)).strip()
        title = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", title)
        if "peer comparison" not in title.casefold():
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections.append(text[heading.end() : end].strip())
    return sections


def _section_is_truncated(body: str) -> bool:
    if len(body) < 40:
        return True
    return not _TERMINAL_PUNCTUATION_RE.search(body)


def _first_heading_without_prose(text: str) -> str:
    headings = list(_MARKDOWN_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end() : end].strip()
        next_heading_is_child = (
            index + 1 < len(headings)
            and len(headings[index + 1].group(1)) > len(heading.group(1))
        )
        if not body and not next_heading_is_child:
            return heading.group(2).strip()
    return ""


def _first_unknown_peer(
    peer_sections: list[str], entities: list[str], forbidden_entities: list[str]
) -> str:
    if not entities:
        return ""
    for body in peer_sections:
        for forbidden in forbidden_entities:
            if forbidden and not any(_same_entity(forbidden, entity) for entity in entities):
                pattern = r"(?<!\w)" + re.escape(forbidden) + r"(?!\w)"
                if re.search(pattern, body, re.IGNORECASE):
                    return forbidden
        candidates: list[str] = []
        candidates.extend(match.group(1) for match in _COMPANY_BEFORE_CUE_RE.finditer(body))
        candidates.extend(match.group(1) for match in _COMPANY_AFTER_CUE_RE.finditer(body))
        candidates.extend(match.group(1) for match in _COMPANY_AFTER_LEADERSHIP_RE.finditer(body))
        for line in body.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and re.match(r"^[A-Z][A-Za-z0-9&.' -]+$", cells[0]):
                candidates.append(cells[0])
        for candidate in candidates:
            if candidate.casefold() in {"company", "issuer", "peer"}:
                continue
            if not any(_same_entity(candidate, entity) for entity in entities):
                return candidate
    return ""


def _same_entity(candidate: str, entity: str) -> bool:
    def normalize(value: str) -> str:
        value = re.sub(r"\b(?:incorporated|inc|corp(?:oration)?|company|co|ltd)\b", "", value, flags=re.I)
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    left = normalize(candidate)
    right = normalize(entity)
    return bool(left and right and (left == right or left in right or right in left))


def _entity_name(entity: Any) -> str:
    if isinstance(entity, str):
        return entity.strip()
    if isinstance(entity, dict):
        return str(entity.get("name") or entity.get("entity") or entity.get("symbol") or "").strip()
    return str(entity).strip()


def _finding(message: str) -> Finding:
    return Finding(
        metric="visible_output_integrity",
        severity="high",
        message=message,
        recommendation="Regenerate the user-visible report without reasoning leakage or truncation.",
        action="rewrite",
        target={"field": "final_output"},
    )
