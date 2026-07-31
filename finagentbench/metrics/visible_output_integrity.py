from __future__ import annotations

import math
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
_DEFAULT_PEER_ALIASES = (
    "Peer Comparison",
    "Comparable Companies",
    "Peer Analysis",
    "同业比较",
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
_TRUNCATED_TAIL_RE = re.compile(
    r"(?:\.\.\.|…|TODO|TBD|<\w+>|\[(?:insert|todo)\])\s*$",
    re.IGNORECASE,
)
_FENCE_RE = re.compile(r"(?m)^```")


def visible_output_integrity(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    """Detect deterministic signs that user-visible output leaked or was truncated.

    Only ``final_output`` is inspected. Case contracts supply peer-section aliases and
    entity aliases; regex company guesses alone never high-block.
    """

    output = str(run.get("final_output") or "")
    findings: list[Finding] = []
    inspectable = _strip_ignored_regions(output)

    marker = _first_phrase(inspectable, _REASONING_MARKERS)
    if marker and _looks_like_meta_reasoning(inspectable, marker):
        findings.append(
            _finding(
                f"Reasoning marker leaked into final output: {marker!r}",
                code="reasoning_leak",
                confidence="high",
            )
        )

    restatement = _first_phrase(inspectable, _PROMPT_RESTATEMENTS)
    if restatement:
        findings.append(
            _finding(
                f"Prompt or task restatement leaked into final output: {restatement!r}",
                code="prompt_restatement",
                confidence="high",
            )
        )

    if _unclosed_code_fence(output):
        findings.append(
            _finding(
                "Unclosed fenced code block in final output.",
                code="unclosed_code_block",
                confidence="high",
            )
        )

    peer_sections = _peer_sections(output, case)
    if any(_section_is_truncated(body) for body in peer_sections):
        findings.append(
            _finding(
                "Peer Comparison section appears truncated.",
                code="truncated_output",
                confidence="high",
            )
        )

    if output.strip() and _obviously_truncated(output):
        findings.append(
            _finding(
                "Final output appears truncated.",
                code="truncated_output",
                confidence="high",
            )
        )
    elif output.strip() and not _looks_structurally_complete(output) and not _TERMINAL_PUNCTUATION_RE.search(
        output.rstrip()
    ):
        findings.append(
            _finding(
                "The final sentence has no ending punctuation.",
                code="truncated_output",
                confidence="low",
                severity="medium",
            )
        )

    empty_heading = _first_heading_without_content(output)
    if empty_heading:
        findings.append(
            _finding(
                f"Markdown heading has no following prose: {empty_heading!r}",
                code="empty_section",
                confidence="high",
            )
        )

    entities = [_entity_name(item) for item in run.get("entities", [])]
    entities = [name for name in entities if name]
    aliases = _entity_alias_map(case)
    for body in peer_sections:
        if len(entities) == 1 and _LEADERSHIP_RE.search(body):
            findings.append(
                _finding(
                    "Single-company report makes a leadership claim in Peer Comparison.",
                    code="invalid_peer_claim",
                    confidence="high",
                )
            )
            break

    forbidden = [_entity_name(item) for item in case.get("forbidden_entities", [])]
    forbidden_hit = _first_forbidden_peer(peer_sections, entities, forbidden, aliases)
    if forbidden_hit:
        findings.append(
            _finding(
                f"Peer Comparison mentions a company outside FinRun entities: {forbidden_hit}",
                code="unknown_peer",
                confidence="high",
            )
        )
    else:
        unknown = _first_unknown_peer(peer_sections, entities, aliases)
        if unknown:
            findings.append(
                _finding(
                    f"Peer Comparison may mention an unrecognized company token: {unknown}",
                    code="unknown_peer",
                    confidence="medium",
                    severity="medium",
                )
            )

    blocking = [f for f in findings if f.severity in {"high", "critical"}]
    return MetricResult(
        "visible_output_integrity",
        100.0 if not blocking else 0.0,
        not blocking,
        findings,
    )


def _strip_ignored_regions(text: str) -> str:
    without_fences = re.sub(r"```.*?```", "\n", text, flags=re.S)
    without_quotes = re.sub(r"(?m)^>.*$", "", without_fences)
    without_quotes = re.sub(r"[\"“].*?[\"”]", " ", without_quotes)
    return without_quotes


def _looks_like_meta_reasoning(text: str, marker: str) -> bool:
    pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, marker.split())) + r"(?!\w)"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start:match.start()].strip().casefold()
        window = text[match.start() : match.start() + 80].casefold()
        if prefix in {"", "-", "*", ">"}:
            return True
        if any(token in window for token in ("draft", "final answer", "report", "summarize", "comply")):
            return True
    return False


def _first_phrase(text: str, phrases: tuple[str, ...]) -> str:
    for phrase in phrases:
        pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, phrase.split())) + r"(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return phrase
    return ""


def _unclosed_code_fence(text: str) -> bool:
    return len(_FENCE_RE.findall(text)) % 2 == 1


def _peer_section_aliases(case: dict[str, Any]) -> list[str]:
    raw = case.get("peer_section_aliases") or list(_DEFAULT_PEER_ALIASES)
    return [str(item).strip() for item in raw if str(item).strip()]


def _peer_sections(text: str, case: dict[str, Any]) -> list[str]:
    aliases = [alias.casefold() for alias in _peer_section_aliases(case)]
    headings = list(_MARKDOWN_HEADING_RE.finditer(text))
    sections: list[str] = []
    for index, heading in enumerate(headings):
        title = re.sub(r"[*_`]+", "", heading.group(2)).strip()
        title = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", title)
        folded = title.casefold()
        if not any(alias == folded or alias in folded for alias in aliases):
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end() : end].strip()
        if not body and index + 1 < len(headings):
            # Empty peer heading before a child/next section is handled by empty_section.
            sections.append(body)
            continue
        sections.append(body)
    return sections


def _section_is_truncated(body: str) -> bool:
    if not body.strip():
        return True
    if _looks_structurally_complete(body):
        return False
    if len(body) < 40 and not _TERMINAL_PUNCTUATION_RE.search(body.rstrip()):
        return True
    return bool(_TRUNCATED_TAIL_RE.search(body.rstrip()))


def _looks_structurally_complete(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    if _TERMINAL_PUNCTUATION_RE.search(stripped):
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not lines:
        return False
    last = lines[-1]
    if last.startswith("|") or last.startswith(("-", "*", "+")):
        return True
    if last.startswith("```") or stripped.endswith("```"):
        return True
    if last.startswith(">"):
        return True
    if _MARKDOWN_HEADING_RE.match(last):
        return False
    return False


def _obviously_truncated(text: str) -> bool:
    stripped = text.rstrip()
    if _TRUNCATED_TAIL_RE.search(stripped):
        return True
    # Incomplete question / clause with no structural closer.
    if stripped.endswith(("Which company leads", "which company leads")):
        return True
    return False


def _first_heading_without_content(text: str) -> str:
    headings = list(_MARKDOWN_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end() : end].strip()
        next_heading_is_child = (
            index + 1 < len(headings)
            and len(headings[index + 1].group(1)) > len(heading.group(1))
        )
        if body:
            if _has_meaningful_body(body):
                continue
            if not next_heading_is_child:
                return heading.group(2).strip()
        elif not next_heading_is_child:
            return heading.group(2).strip()
    return ""


def _has_meaningful_body(body: str) -> bool:
    if not body.strip():
        return False
    if re.search(r"(?m)^\|", body):
        return True
    if re.search(r"(?m)^(?:[-*+]|\d+\.)\s+\S", body):
        return True
    if "```" in body:
        return True
    if re.search(r"(?m)^>", body):
        return True
    if re.search(r"(?m)^#{1,6}\s+\S", body):
        return True
    return bool(re.search(r"[A-Za-z0-9\u4e00-\u9fff]", body))


def _entity_alias_map(case: dict[str, Any]) -> dict[str, list[str]]:
    raw = case.get("entity_aliases") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, values in raw.items():
        names = [str(key)]
        if isinstance(values, list):
            names.extend(str(v) for v in values)
        elif values:
            names.append(str(values))
        out[str(key)] = names
    return out


def _all_known_names(entities: list[str], aliases: dict[str, list[str]]) -> list[str]:
    names = list(entities)
    for key, values in aliases.items():
        names.append(key)
        names.extend(values)
    return [name for name in names if name]


def _first_forbidden_peer(
    peer_sections: list[str],
    entities: list[str],
    forbidden_entities: list[str],
    aliases: dict[str, list[str]],
) -> str:
    known = _all_known_names(entities, aliases)
    for body in peer_sections:
        for forbidden in forbidden_entities:
            if not forbidden:
                continue
            if any(_same_entity(forbidden, entity) for entity in known):
                continue
            pattern = r"(?<!\w)" + re.escape(forbidden) + r"(?!\w)"
            if re.search(pattern, body, re.IGNORECASE):
                return forbidden
    return ""


def _first_unknown_peer(
    peer_sections: list[str],
    entities: list[str],
    aliases: dict[str, list[str]],
) -> str:
    if not entities:
        return ""
    known = _all_known_names(entities, aliases)
    for body in peer_sections:
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
            if not any(_same_entity(candidate, entity) for entity in known):
                return candidate
    return ""


def _same_entity(candidate: str, entity: str) -> bool:
    def normalize(value: str) -> str:
        value = re.sub(
            r"\b(?:incorporated|inc|corp(?:oration)?|company|co|ltd)\b",
            "",
            value,
            flags=re.I,
        )
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


def _finding(
    message: str,
    *,
    code: str,
    confidence: str,
    severity: str = "high",
) -> Finding:
    return Finding(
        metric="visible_output_integrity",
        severity=severity,
        message=message,
        recommendation="Regenerate the user-visible report without reasoning leakage or truncation.",
        action="rewrite",
        target={"field": "final_output", "code": code, "confidence": confidence},
    )
