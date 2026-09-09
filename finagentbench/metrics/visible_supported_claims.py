"""Bind user-visible financial assertions in ``final_output`` to verified facts.

This is not ``visible_output_integrity`` (leak/truncation) and not
``numeric_correctness`` (structured formula recompute). Unverifiable prose
without an entity+metric cue is left unchecked.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from ..schema import DEFAULT_SCORING_VERSION, Finding, MetricResult
from .common import empty_check_result, input_currency, input_unit, input_value


RATIO_ALIASES: dict[str, tuple[str, ...]] = {
    "ebitda_margin": ("ebitda margin", "ebitda-margin"),
    "operating_margin": ("operating margin",),
    "r_and_d_intensity": (
        "r&d intensity",
        "r and d intensity",
        "research and development intensity",
        "rd intensity",
    ),
}
ABSOLUTE_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "revenues", "net sales", "total revenue"),
    "ebitda": ("ebitda",),
    "r_and_d": ("r&d", "r and d", "research and development"),
    "operating_income": ("operating income", "operating profit"),
}
_IGNORE_NUMBER_PREFIX = re.compile(
    r"(?:fy|q[1-4]|page|p\.?|#p|table|section|step|figure|chapter)\s*$",
    re.IGNORECASE,
)
_FENCE_RE = re.compile(r"(?s)```.*?```")
_PERIOD_RE = re.compile(
    r"\bFY\s*(20\d{2})\b|"
    r"(?<![\d-])\b(20\d{2})\b(?!-\d{2})",
    re.IGNORECASE,
)
_FULL_NUMBER_RE = re.compile(
    r"(?<![\d.])(?P<num>[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?![\d.])"
)
_PERCENT_TAIL_RE = re.compile(r"^\s*(%|percent\b|pct\b)", re.IGNORECASE)
_SCI_TAIL_RE = re.compile(r"^[eE][+-]?\d")
_SCALE_TAIL_RE = re.compile(r"^\s*(trillion|billion|million)\b", re.IGNORECASE)
_CURRENCY_TOKEN_RE = re.compile(
    r"(USD|EUR|GBP|CNY|RMB|JPY|AUD|CAD|HKD|CHF|US\$|\$)",
    re.IGNORECASE,
)
_UNDISCLOSED_RE = re.compile(
    r"\b(not disclosed|undisclosed|not reported|not available in this (?:document|filing)|no (?:audited )?(?:revenue|ebitda) (?:figure|amount|data))\b",
    re.IGNORECASE,
)
_CITATION_RE = re.compile(
    r"\[([^\[\]]+)\]"
    r"|(?<![\w.])([\w./-]+\.(?:pdf|md|html|htm|txt)#p\d+)"
    r"|(lumenfin:[\w:.-]+)"
    r"|(10-[KQ](?:/A)?)",
    re.IGNORECASE,
)
_LEAD_RE = re.compile(
    r"\b(?:leads?|outperforms?|higher(?:\s+\w+){0,5}\s+than|greater(?:\s+\w+){0,5}\s+than|above)\b",
    re.IGNORECASE,
)
_TRAIL_RE = re.compile(
    r"\b(?:trails?|lags?|lower(?:\s+\w+){0,5}\s+than|below|worse(?:\s+\w+){0,5}\s+than)\b",
    re.IGNORECASE,
)
_STOP_ENTITIES = frozenset(
    {
        "the",
        "this",
        "that",
        "see",
        "table",
        "section",
        "figure",
        "page",
        "ebitda",
        "usd",
        "fy",
        "while",
        "research",
        "disclaimer",
    }
)
_MONEY_UNITS = frozenset({"billion", "million", "trillion", "usd", "us$", "$", "eur", "gbp"})
_SCALE_WORDS = {"million": 1e6, "billion": 1e9, "trillion": 1e12}
_CURRENCY_WORDS = {
    "usd": "USD",
    "us$": "USD",
    "eur": "EUR",
    "euro": "EUR",
    "gbp": "GBP",
    "cny": "CNY",
    "rmb": "CNY",
    "jpy": "JPY",
    "aud": "AUD",
    "cad": "CAD",
    "hkd": "HKD",
    "chf": "CHF",
}
_KNOWN_ISO = frozenset({"USD", "EUR", "GBP", "CNY", "JPY", "AUD", "CAD", "HKD", "CHF"})
_CURRENCY_STOPWORDS = frozenset(
    {"for", "the", "and", "was", "has", "are", "but", "not", "per", "net", "its", "our", "fy", "see", "with", "from"}
)
_PERCENT_UNITS = frozenset({"%", "percent", "pct", "ratio"})


@dataclass(frozen=True)
class VisibleAmount:
    value: float
    percent: bool
    scale: float | None
    currency: str
    raw: str
    start: int
    unparsed: bool = False


@dataclass(frozen=True)
class VisibleAssertion:
    entity: str
    metric: str
    kind: str
    amount: VisibleAmount
    period: str
    citations: tuple[str, ...]
    sentence: str
    origin: str = "prose"
    row: int = -1
    column: int = -1


@dataclass(frozen=True)
class SupportedFact:
    entity: str
    metric: str
    value: float
    unit: str
    period: str
    currency: str = ""
    kind: str = "metric"
    citations: tuple[str, ...] = ()
    required_citations: tuple[str, ...] = ()


def visible_supported_claims(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    scoring = str(case.get("scoring_version") or DEFAULT_SCORING_VERSION)
    explicit = "visible_supported_claims" in (case.get("enabled_metrics") or [])
    if scoring != "3" and not explicit:
        return MetricResult("visible_supported_claims", 100.0, True, [])
    output = str(run.get("final_output") or "")
    inspectable = _FENCE_RE.sub(" ", output)
    facts = _catalog(run, case)
    if not facts:
        empty = empty_check_result(
            "visible_supported_claims",
            case,
            detail="no verified metrics/claims were exported to compare against visible prose",
        )
        if empty is not None:
            return empty
        return MetricResult("visible_supported_claims", 100.0, True, [])

    findings: list[Finding] = []
    entity_names = _entity_names(run, case)
    require_citations = bool(case.get("require_visible_claim_citations"))
    evidence_rows = [item for item in (run.get("evidence") or []) if isinstance(item, dict)]
    assertions = parse_visible_assertions(inspectable, entity_names)
    checked = 0
    for assertion in assertions:
        checked += _score_assertion(
            assertion,
            facts,
            case,
            findings,
            require_citations=require_citations,
            evidence_rows=evidence_rows,
        )
    for sentence in _sentences(inspectable):
        if _skip_sentence(sentence):
            continue
        _check_direction(sentence, facts, entity_names, _alias_index(), findings)

    if checked == 0:
        empty = empty_check_result(
            "visible_supported_claims",
            case,
            detail="final_output had no entity+metric numeric assertions to verify",
        )
        if empty is not None:
            return empty
        return MetricResult("visible_supported_claims", 100.0, True, findings)

    failed = [item for item in findings if item.severity in {"high", "critical"}]
    score = 0.0 if failed else 100.0
    blocked = not failed
    return MetricResult("visible_supported_claims", score, blocked and not failed, findings)


def _catalog(run: dict[str, Any], case: dict[str, Any]) -> list[SupportedFact]:
    facts: list[SupportedFact] = []
    for metric in run.get("metrics") or []:
        entity = str(metric.get("entity") or "")
        name = str(metric.get("name") or "")
        try:
            value = float(metric.get("value"))
        except (TypeError, ValueError):
            continue
        if not entity or not name:
            continue
        cites, required = _citation_bundle(run, metric, entity, name, str(metric.get("period") or ""))
        facts.append(
            SupportedFact(
                entity=entity,
                metric=name,
                value=value,
                unit=str(metric.get("unit") or ("ratio" if name in RATIO_ALIASES else "")),
                period=str(metric.get("period") or ""),
                currency=str(metric.get("currency") or ""),
                kind="metric",
                citations=cites,
                required_citations=required,
            )
        )
        inputs = metric.get("inputs") or {}
        if isinstance(inputs, dict):
            for input_name, payload in inputs.items():
                raw = input_value(payload)
                try:
                    input_val = float(raw)
                except (TypeError, ValueError):
                    continue
                period = str((payload or {}).get("period") if isinstance(payload, dict) else metric.get("period") or "")
                cites, required = _citation_bundle(
                    run,
                    payload if isinstance(payload, dict) else {},
                    entity,
                    str(input_name),
                    period,
                    must_support=True,
                    expected_value=input_val,
                    expected_unit=input_unit(payload) if isinstance(payload, dict) else "billion",
                    expected_currency=input_currency(payload) if isinstance(payload, dict) else "",
                )
                facts.append(
                    SupportedFact(
                        entity=entity,
                        metric=str(input_name),
                        value=input_val,
                        unit=input_unit(payload) or "billion",
                        period=period,
                        currency=input_currency(payload),
                        kind="input",
                        citations=cites,
                        required_citations=required,
                    )
                )
    for claim in run.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        verification = str(claim.get("verification") or "").lower()
        if verification in {"unverified", "rejected"}:
            continue
        if claim.get("verified") is False:
            continue
        entity = str(claim.get("entity") or "")
        name = str(claim.get("metric_name") or "")
        raw = claim.get("value")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if not entity or not name:
            continue
        cites, required = _citation_bundle(
            run, claim, entity, name, str(claim.get("period") or ""), expected_value=None if name in RATIO_ALIASES else value
        )
        facts.append(
            SupportedFact(
                entity=entity,
                metric=name,
                value=value,
                unit=str(claim.get("unit") or ""),
                period=str(claim.get("period") or ""),
                currency=str(claim.get("currency") or ""),
                kind="claim",
                citations=cites,
                required_citations=required,
            )
        )
    return facts


def _entity_names(run: dict[str, Any], case: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in run.get("entities") or []:
        if isinstance(item, str):
            if item:
                names.append(item)
            continue
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item.get("name")))
    for extra in case.get("expected_entities") or []:
        if extra and str(extra) not in names:
            names.append(str(extra))
    aliases = case.get("entity_aliases") or {}
    for canonical, items in aliases.items():
        names.append(str(canonical))
        if isinstance(items, str):
            names.append(items)
        else:
            names.extend(str(item) for item in items or [])
    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        unique.append(name)
    unique.sort(key=len, reverse=True)
    return unique


def _alias_index() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for metric, aliases in {**RATIO_ALIASES, **ABSOLUTE_ALIASES}.items():
        kind = "ratio" if metric in RATIO_ALIASES else "absolute"
        for alias in aliases:
            rows.append((alias, metric, kind))
    rows.sort(key=lambda item: len(item[0]), reverse=True)
    return rows


def _sentences(text: str) -> list[str]:
    chunks: list[str] = []
    for block in re.split(r"(?:[.!?。](?=\s+[A-Z]|$)|\n+|；|;)+", text):
        item = block.strip(" \t-*#")
        if item:
            chunks.append(item)
    return chunks


def _skip_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if lowered.startswith(("##", "#")):
        return True
    if re.fullmatch(r"(?:page|p\.?|#p|table|section|step|figure)\s*\d+", lowered):
        return True
    return False


def _table_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell)


def _header_spec(cell: str, entity_names: list[str]) -> dict[str, Any]:
    lowered = cell.lower().strip()
    if lowered in {"company", "entity", "issuer"}:
        return {"role": "entity"}
    if lowered in {"metric", "indicator", "measure"}:
        return {"role": "metric"}
    if lowered in {"value", "amount", "figure"}:
        return {"role": "value"}
    if lowered in {"source", "citation", "citations", "evidence"}:
        return {"role": "citation"}
    if lowered in {"period", "year", "fy"}:
        return {"role": "period"}
    if lowered in {"statement", "claim", "description", "notes"}:
        return {"role": "prose"}
    if any(
        token in lowered
        for token in ("internal screen", "vs screen", "status", "level", "type")
    ):
        return {"role": "ignore"}
    for name in entity_names:
        if name.lower() == lowered:
            return {"role": "entity_value", "entity": name}
    period = _period_in(cell)
    for alias, metric_name, kind in _alias_index():
        if alias in lowered:
            return {"role": "metric_value", "metric": metric_name, "kind": kind, "period": period}
    return {"role": "other"}


def _cell_looks_financial(cell: str) -> bool:
    lowered = cell.lower()
    if re.search(r"\d", cell) and (
        "%" in cell
        or re.search(r"\b(billion|million|trillion|usd|eur|gbp|cny)\b", lowered)
        or "$" in cell
    ):
        return True
    return bool(_FULL_NUMBER_RE.search(cell) and re.search(r"\b(margin|revenue|ebitda|intensity)\b", lowered))


def _assertions_from_table(
    block: list[str],
    entity_names: list[str],
    discourse_entity: str,
    discourse_period: str,
) -> tuple[list[VisibleAssertion], bool]:
    rows = [ _table_cells(line) for line in block if line.strip() ]
    if not rows:
        return [], False
    header = rows[0]
    header_names = {cell.strip().lower() for cell in header}
    # Retrieval catalogs and claim ledgers are not financial fact tables.
    if {"citation", "excerpt"}.issubset(header_names) or {"citation", "method"}.issubset(
        header_names
    ):
        return [], False
    body = rows[1:]
    if body and _is_separator_row(body[0]):
        body = body[1:]
    specs = [_header_spec(cell, entity_names) for cell in header]
    assertions: list[VisibleAssertion] = []
    mapped = False
    entity_col = next((i for i, spec in enumerate(specs) if spec["role"] == "entity"), None)
    metric_col = next((i for i, spec in enumerate(specs) if spec["role"] == "metric"), None)
    value_col = next((i for i, spec in enumerate(specs) if spec["role"] == "value"), None)
    cite_col = next((i for i, spec in enumerate(specs) if spec["role"] == "citation"), None)
    period_col = next((i for i, spec in enumerate(specs) if spec["role"] == "period"), None)
    prose_col = next((i for i, spec in enumerate(specs) if spec["role"] == "prose"), None)
    metric_value_cols = [i for i, spec in enumerate(specs) if spec["role"] == "metric_value"]
    entity_value_cols = [i for i, spec in enumerate(specs) if spec["role"] == "entity_value"]
    ignore_cols = {i for i, spec in enumerate(specs) if spec["role"] == "ignore"}

    for row_idx, cells in enumerate(body, start=1):
        def cell_at(index: int | None) -> str:
            if index is None or index >= len(cells):
                return ""
            return cells[index]

        row_citations = tuple(_citations(" ".join(cells)))
        row_period = _period_in(" ".join(cells)) or discourse_period
        if period_col is not None:
            row_period = _period_in(cell_at(period_col)) or row_period
        row_entity = cell_at(entity_col) if entity_col is not None else discourse_entity
        if entity_col is not None:
            for name in entity_names:
                if name.lower() == row_entity.lower():
                    row_entity = name
                    break

        if metric_value_cols and row_entity:
            for col in metric_value_cols:
                spec = specs[col]
                amount = _amount_after(cell_at(col), 0)
                if amount is None:
                    if _cell_looks_financial(cell_at(col)):
                        amount = VisibleAmount(0.0, False, None, "", cell_at(col), 0, unparsed=True)
                    else:
                        continue
                mapped = True
                assertions.append(
                    VisibleAssertion(
                        entity=row_entity,
                        metric=str(spec["metric"]),
                        kind=str(spec["kind"]),
                        amount=amount,
                        period=str(spec.get("period") or row_period),
                        citations=tuple(_citations(cell_at(col))) or row_citations,
                        sentence=f"{row_entity} {header[col]} {cell_at(col)}".strip(),
                        origin="table",
                        row=row_idx,
                        column=col,
                    )
                )
            continue

        if entity_value_cols and metric_col is not None:
            metric_text = cell_at(metric_col)
            metric_name = None
            kind = "absolute"
            for alias, name, metric_kind in _alias_index():
                if alias in metric_text.lower():
                    metric_name = name
                    kind = metric_kind
                    break
            if metric_name is None:
                continue
            for col in entity_value_cols:
                amount = _amount_after(cell_at(col), 0)
                if amount is None:
                    if _cell_looks_financial(cell_at(col)):
                        amount = VisibleAmount(0.0, False, None, "", cell_at(col), 0, unparsed=True)
                    else:
                        continue
                mapped = True
                assertions.append(
                    VisibleAssertion(
                        entity=str(specs[col]["entity"]),
                        metric=metric_name,
                        kind=kind,
                        amount=amount,
                        period=_period_in(metric_text) or row_period,
                        citations=tuple(_citations(cell_at(col))) or row_citations,
                        sentence=f"{specs[col]['entity']} {metric_text} {cell_at(col)}".strip(),
                        origin="table",
                        row=row_idx,
                        column=col,
                    )
                )
            continue

        if metric_col is not None and value_col is not None and row_entity:
            metric_text = cell_at(metric_col)
            metric_name = None
            kind = "absolute"
            for alias, name, metric_kind in _alias_index():
                if alias in metric_text.lower():
                    metric_name = name
                    kind = metric_kind
                    break
            amount = _amount_after(cell_at(value_col), 0)
            if metric_name and amount is not None:
                mapped = True
                cite = tuple(_citations(cell_at(cite_col))) if cite_col is not None else ()
                assertions.append(
                    VisibleAssertion(
                        entity=row_entity,
                        metric=metric_name,
                        kind=kind,
                        amount=amount,
                        period=_period_in(metric_text) or row_period,
                        citations=cite or row_citations,
                        sentence=f"{row_entity} {metric_text} {cell_at(value_col)}".strip(),
                        origin="table",
                        row=row_idx,
                        column=value_col,
                    )
                )

        if prose_col is not None:
            extra, row_entity, row_period = _assertions_from_sentence(
                cell_at(prose_col), entity_names, row_entity, row_period
            )
            source_cites = tuple(_citations(cell_at(cite_col))) if cite_col is not None else ()
            for item in extra:
                citations = source_cites or item.citations or row_citations
                assertions.append(
                    VisibleAssertion(
                        entity=item.entity,
                        metric=item.metric,
                        kind=item.kind,
                        amount=item.amount,
                        period=item.period,
                        citations=citations,
                        sentence=item.sentence,
                        origin="table",
                        row=row_idx,
                        column=prose_col,
                    )
                )
            if extra:
                mapped = True

    unparsed = False
    if not mapped and any(
        _cell_looks_financial(cell)
        for row in body
        for idx, cell in enumerate(row)
        if idx not in ignore_cols
    ):
        unparsed = True
    return assertions, unparsed


def _assertions_from_sentence(
    sentence: str,
    entity_names: list[str],
    discourse_entity: str,
    discourse_period: str,
) -> tuple[list[VisibleAssertion], str, str]:
    assertions: list[VisibleAssertion] = []
    if _skip_sentence(sentence):
        return assertions, discourse_entity, discourse_period
    mentioned = _entities_in_order(sentence, entity_names)
    if mentioned:
        discourse_entity = mentioned[-1]
    period_here = _period_in(sentence)
    if period_here:
        discourse_period = period_here
    lowered = sentence.lower()
    used_spans: list[tuple[int, int]] = []
    for alias, metric_name, kind in _alias_index():
        for match in re.finditer(rf"(?<![\w]){re.escape(alias)}(?![\w])", lowered):
            alias_at = match.start()
            alias_end = match.end()
            if any(start <= alias_at < end or start < alias_end <= end for start, end in used_spans):
                continue
            remainder = lowered[alias_at:]
            if any(
                other != alias and other.startswith(alias) and remainder.startswith(other)
                for other, _, _ in _alias_index()
            ):
                continue
            unknown = _unknown_entity_before(sentence, entity_names, alias_at)
            entity = _entity_before(sentence, entity_names, alias_at)
            if entity is None:
                entity = unknown or discourse_entity or None
            if entity is None:
                continue
            amount = _amount_after(sentence, alias_end)
            if amount is None:
                continue
            if not amount.unparsed and _looks_like_nonfinancial_count(sentence, amount.start, alias_at):
                continue
            used_spans.append((alias_at, alias_end))
            assertions.append(
                VisibleAssertion(
                    entity=entity,
                    metric=metric_name,
                    kind=kind,
                    amount=amount,
                    period=_period_in(sentence) or discourse_period,
                    citations=tuple(_citations(sentence)),
                    sentence=sentence,
                )
            )
    return assertions, discourse_entity, discourse_period


def parse_visible_assertions(text: str, entity_names: list[str]) -> list[VisibleAssertion]:
    """Parse entity/metric/amount/period/currency/citation tuples from prose and tables."""
    inspectable = _FENCE_RE.sub(" ", text)
    assertions: list[VisibleAssertion] = []
    discourse_entity = ""
    discourse_period = ""
    lines = inspectable.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        heading = re.match(r"^#{1,6}\s+(.+)$", raw.strip())
        if heading:
            title = heading.group(1).strip()
            for name in entity_names:
                if re.search(rf"\b{re.escape(name)}\b", title, re.IGNORECASE):
                    discourse_entity = name
            period_here = _period_in(title)
            if period_here:
                discourse_period = period_here
            i += 1
            continue
        if raw.strip().startswith("|"):
            block: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            parsed, unparsed = _assertions_from_table(
                block, entity_names, discourse_entity, discourse_period
            )
            assertions.extend(parsed)
            if unparsed:
                assertions.append(
                    VisibleAssertion(
                        entity=discourse_entity or "unknown",
                        metric="_unparsed_table",
                        kind="absolute",
                        amount=VisibleAmount(0.0, False, None, "", "\n".join(block[:3]), 0, True),
                        period=discourse_period,
                        citations=(),
                        sentence="\n".join(block[:6]),
                        origin="table",
                    )
                )
            continue
        for sentence in _sentences(raw):
            extra, discourse_entity, discourse_period = _assertions_from_sentence(
                sentence, entity_names, discourse_entity, discourse_period
            )
            assertions.extend(extra)
        i += 1
    return assertions


def _score_assertion(
    assertion: VisibleAssertion,
    facts: list[SupportedFact],
    case: dict[str, Any],
    findings: list[Finding],
    *,
    require_citations: bool,
    evidence_rows: list[dict[str, Any]],
) -> int:
    entity = assertion.entity
    metric_name = assertion.metric
    amount = assertion.amount
    period = assertion.period
    kind = assertion.kind
    extra_loc = {"origin": assertion.origin, "row": assertion.row, "column": assertion.column}
    if metric_name == "_unparsed_table" or amount.unparsed:
        findings.append(
            _finding(
                "visible_unparsed_table" if metric_name == "_unparsed_table" else "visible_unparsed_amount",
                (
                    f"Financial table could not be mapped to entity/metric cells: {assertion.sentence[:180]}"
                    if metric_name == "_unparsed_table"
                    else f"{entity} {metric_name} amount {amount.raw!r} is outside the supported numeric grammar."
                ),
                extra={
                    "entity": entity,
                    "metric": metric_name,
                    "code": "unparsed_table" if metric_name == "_unparsed_table" else "unparsed_number",
                    **extra_loc,
                },
            )
        )
        return 1
    unit_hint = "percent" if amount.percent else (
        {1e12: "trillion", 1e9: "billion", 1e6: "million"}.get(amount.scale or 0, "")
    )
    matches = [
        fact
        for fact in facts
        if fact.entity.lower() == entity.lower() and fact.metric == metric_name
    ]
    if not matches:
        findings.append(
            _finding(
                "unsupported_entity_metric",
                f"Visible {metric_name} assertion for {entity} is not backed by verified metrics/claims.",
                extra={"entity": entity, "metric": metric_name, "code": "wrong_entity"},
            )
        )
        return 1
    fact = _best_fact(matches, period)
    if not _values_close(
        amount.value,
        fact,
        percent=amount.percent,
        unit_hint=unit_hint,
        observed_currency=amount.currency,
        observed_scale=amount.scale,
        case=case,
    ):
        findings.append(
            _finding(
                "visible_numeric_mismatch",
                (
                    f"{entity} {metric_name} in final_output is {amount.value}"
                    f"{'%' if amount.percent else ''} but verified value is {fact.value} ({fact.unit or 'numeric'})."
                ),
                        extra={"entity": entity, "metric": metric_name, "code": "wrong_number", "origin": assertion.origin, "row": assertion.row, "column": assertion.column},
            )
        )
    if _period_has_year(period) and not _periods_compatible(period, fact.period or ""):
        findings.append(
            _finding(
                "visible_period_mismatch",
                f"{entity} {metric_name} is stated for {period} but verified period is {fact.period or 'unknown'}.",
                extra={"entity": entity, "metric": metric_name, "code": "wrong_period"},
            )
        )
    if kind == "ratio" and unit_hint in _MONEY_UNITS:
        findings.append(
            _finding(
                "visible_unit_mismatch",
                f"{entity} {metric_name} is a ratio/percent but final_output uses {unit_hint}.",
                extra={"entity": entity, "metric": metric_name, "code": "wrong_unit"},
            )
        )
    if kind == "absolute" and amount.percent:
        findings.append(
            _finding(
                "visible_unit_mismatch",
                f"{entity} {metric_name} is an absolute amount but final_output uses a percent.",
                extra={"entity": entity, "metric": metric_name, "code": "wrong_unit"},
            )
        )
    citations = list(assertion.citations)
    allowed = _allowed_citations(fact, evidence_rows)
    required = {item.strip().lower() for item in fact.required_citations if item.strip()}
    if citations:
        if not any(_citation_matches_fact(token, allowed) for token in citations):
            findings.append(
                _finding(
                    "visible_citation_mismatch",
                    f"{entity} {metric_name} cites {citations[0]!r} which does not support this fact.",
                    extra={"entity": entity, "metric": metric_name, "code": "wrong_citation"},
                )
            )
        elif required and not required.issubset({token.strip().lower() for token in citations}):
            findings.append(
                _finding(
                    "visible_citation_mismatch",
                    f"{entity} {metric_name} is missing required input evidence citations.",
                    extra={"entity": entity, "metric": metric_name, "code": "partial_citation"},
                )
            )
    elif require_citations:
        findings.append(
            _finding(
                "visible_citation_missing",
                f"{entity} {metric_name} assertion has no evidence citation in final_output.",
                extra={"entity": entity, "metric": metric_name, "code": "missing_citation"},
            )
        )
    return 1


def _check_direction(
    sentence: str,
    facts: list[SupportedFact],
    entity_names: list[str],
    alias_index: list[tuple[str, str, str]],
    findings: list[Finding],
) -> None:
    lead = _LEAD_RE.search(sentence)
    trail = _TRAIL_RE.search(sentence)
    if not lead and not trail:
        return
    metric_name = None
    lowered = sentence.lower()
    for alias, name, _kind in alias_index:
        if alias in lowered:
            metric_name = name
            break
    if metric_name is None:
        return
    mentioned = _entities_in_order(sentence, entity_names)
    if len(mentioned) < 2:
        return
    left, right = mentioned[0], mentioned[1]
    left_val = _metric_value(facts, left, metric_name)
    right_val = _metric_value(facts, right, metric_name)
    if left_val is None or right_val is None:
        return
    if lead and left_val <= right_val:
        findings.append(
            _finding(
                "visible_direction_mismatch",
                f"{left} does not lead {right} on {metric_name} ({left_val} vs {right_val}).",
                extra={"entity": left, "metric": metric_name, "code": "wrong_direction"},
            )
        )
    if trail and left_val >= right_val:
        findings.append(
            _finding(
                "visible_direction_mismatch",
                f"{left} does not trail {right} on {metric_name} ({left_val} vs {right_val}).",
                extra={"entity": left, "metric": metric_name, "code": "wrong_direction"},
            )
        )


def _entities_in_order(sentence: str, entity_names: list[str]) -> list[str]:
    found: list[tuple[int, str]] = []
    for name in entity_names:
        for match in re.finditer(rf"\b{re.escape(name)}\b", sentence, re.IGNORECASE):
            found.append((match.start(), name))
    found.sort()
    ordered: list[str] = []
    seen: set[str] = set()
    for _at, name in found:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(name)
    return ordered


def _unknown_entity_before(sentence: str, entity_names: list[str], alias_at: int) -> str | None:
    window = sentence[:alias_at]
    known = {name.lower() for name in entity_names}
    found = None
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9&.'-]*)\b", window):
        token = match.group(1)
        if token.lower() in _STOP_ENTITIES or token.lower() in known:
            continue
        found = token
    return found


def _entity_before(sentence: str, entity_names: list[str], alias_at: int) -> str | None:
    window = sentence[: alias_at + 1]
    found: str | None = None
    found_at = -1
    for name in entity_names:
        for match in re.finditer(rf"\b{re.escape(name)}\b", window, re.IGNORECASE):
            if match.start() >= found_at:
                found_at = match.start()
                found = name
    return found


def _amount_after(sentence: str, start: int) -> VisibleAmount | None:
    region = sentence[start:]
    for match in _FULL_NUMBER_RE.finditer(region[:120]):
        prefix = (sentence[max(0, start + match.start() - 12) : start + match.start()]).lower()
        if _IGNORE_NUMBER_PREFIX.search(prefix.strip()):
            continue
        raw = match.group("num")
        rest = region[match.end() :]
        if _SCI_TAIL_RE.match(rest):
            sci = raw + rest[:16].split()[0]
            return VisibleAmount(
                value=0.0,
                percent=False,
                scale=None,
                currency="",
                raw=sci,
                start=start + match.start(),
                unparsed=True,
            )
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if re.fullmatch(r"20\d{2}", raw.replace(",", "")) and not _PERCENT_TAIL_RE.match(rest):
            continue
        percent = bool(_PERCENT_TAIL_RE.match(rest))
        scale = None
        currency = ""
        cursor = rest
        scale_match = _SCALE_TAIL_RE.match(cursor)
        if scale_match:
            scale = _SCALE_WORDS[scale_match.group(1).lower()]
            cursor = cursor[scale_match.end() :]
        post = re.match(
            r"^\s*([A-Za-z]{3}|us\$|\$|euro|cny|rmb)\b",
            cursor,
            re.IGNORECASE,
        )
        if post:
            currency = _normalize_currency_token(post.group(1))
        if not currency:
            pre_window = sentence[max(0, start + match.start() - 12) : start + match.start()]
            pre_tokens = list(_CURRENCY_TOKEN_RE.finditer(pre_window))
            if pre_tokens:
                currency = _normalize_currency_token(pre_tokens[-1].group(1))
        return VisibleAmount(
            value=value,
            percent=percent,
            scale=scale,
            currency=currency,
            raw=raw,
            start=start + match.start(),
        )
    return None


def _looks_like_nonfinancial_count(sentence: str, number_at: int, alias_at: int) -> bool:
    window = sentence[max(0, number_at - 20) : number_at].lower()
    return bool(re.search(r"\b(steps?|specialists?|nodes?|agents?|pages?|sections?)\b", window))


def _period_in(sentence: str) -> str:
    match = _PERIOD_RE.search(sentence)
    if not match:
        return ""
    year = match.group(1) or match.group(2)
    return f"FY{year}" if year else ""


def _citations(sentence: str) -> list[str]:
    found: list[str] = []
    for match in _CITATION_RE.finditer(sentence):
        token = next((group for group in match.groups() if group), "")
        if token:
            found.append(token)
    return found


def _normalize_currency_token(token: str) -> str:
    raw = token.strip().lower().replace(".", "")
    if not raw or raw in _CURRENCY_STOPWORDS:
        return ""
    if raw == "$":
        return "USD"
    mapped = _CURRENCY_WORDS.get(raw)
    if mapped:
        return mapped
    if raw.isalpha() and len(raw) == 3:
        return raw.upper()
    return ""


def _metric_aliases(metric_name: str) -> tuple[str, ...]:
    extra = RATIO_ALIASES.get(metric_name, ()) + ABSOLUTE_ALIASES.get(metric_name, ())
    readable = metric_name.replace("_", " ")
    return tuple(dict.fromkeys((metric_name, readable, *extra)))


def _explicit_citation_tokens(payload: dict[str, Any]) -> tuple[str, ...]:
    found: list[str] = []
    single = payload.get("citation")
    if single:
        found.append(str(single).strip())
    for key in ("citations", "evidence_ids", "evidence"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            found.append(raw.strip())
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    token = str(item.get("citation") or item.get("id") or "").strip()
                else:
                    token = str(item).strip()
                if token:
                    found.append(token)
    return tuple(dict.fromkeys(item for item in found if item))


def _resolve_evidence_token(run: dict[str, Any], token: str) -> str:
    needle = token.strip()
    if not needle:
        return ""
    for item in run.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        citation = str(item.get("citation") or "").strip()
        identity = str(item.get("id") or item.get("evidence_id") or item.get("chunk_id") or "").strip()
        if needle == citation or needle == identity:
            return citation or needle
    return needle


def _scale_in(window: str) -> float | None:
    lowered = window.lower()
    for token, factor in _SCALE_WORDS.items():
        if token in lowered:
            return factor
    return None


def _evidence_row_for_token(run: dict[str, Any], token: str) -> dict[str, Any] | None:
    needle = token.strip().lower()
    if not needle:
        return None
    for item in run.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("id") or item.get("evidence_id") or item.get("chunk_id") or "").strip().lower()
        citation = str(item.get("citation") or "").strip().lower()
        record = str(item.get("source_record_id") or "").strip().lower()
        if needle in {identity, citation, record}:
            return item
    return None


def _structured_metric_names(item: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("metric", "name"):
        if item.get(key):
            names.add(str(item.get(key)).strip().lower())
    listed = item.get("metrics") or []
    if isinstance(listed, list):
        names.update(str(entry).strip().lower() for entry in listed if str(entry).strip())
    values = item.get("values")
    if isinstance(values, dict):
        names.update(str(key).strip().lower() for key in values)
    return names


def _finite_number(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _evidence_quantity_matches(
    item: dict[str, Any],
    *,
    expected_value: float | None,
    expected_unit: str,
    expected_currency: str,
) -> bool:
    observed = _finite_number(item.get("value"))
    values = item.get("values") if isinstance(item.get("values"), dict) else {}
    if observed is None and values:
        for raw in values.values():
            observed = _finite_number(raw)
            if observed is not None:
                break
    if observed is None:
        return False
    ev_unit = str(item.get("unit") or "")
    ev_currency = str(item.get("currency") or "").upper()
    exp_currency = str(expected_currency or "").upper()
    if ev_currency and exp_currency and ev_currency != exp_currency:
        return False
    if exp_currency and not ev_currency:
        return False
    if ev_currency and not exp_currency and ev_currency not in {"USD", ""}:
        return False
    if expected_value is None:
        return True
    ev_scale = _scale_in(ev_unit) or 1.0
    exp_scale = _scale_in(expected_unit) or 1.0
    expected = _finite_number(expected_value)
    if expected is None:
        return False
    tol = max(abs(expected * exp_scale) * 0.01, 0.05 * max(ev_scale, exp_scale))
    return math.isclose(observed * ev_scale, expected * exp_scale, abs_tol=tol, rel_tol=0.0)


def _evidence_supports_metric(
    item: dict[str, Any],
    metric_name: str,
    *,
    expected_value: float | None = None,
    expected_unit: str = "",
    expected_currency: str = "",
) -> bool:
    if _UNDISCLOSED_RE.search(str(item.get("text") or "")):
        return False
    names = _structured_metric_names(item)
    aliases = {metric_name.lower(), *{alias.lower() for alias in _metric_aliases(metric_name)}}
    if not names.intersection(aliases):
        return False
    raw = item.get("value")
    values = item.get("values") if isinstance(item.get("values"), dict) else {}
    if raw is None:
        raw = values.get(metric_name)
        if raw is None:
            for alias in aliases:
                if alias in values:
                    raw = values[alias]
                    break
    if _finite_number(raw) is None:
        return False
    return _evidence_quantity_matches(
        {**item, "value": raw},
        expected_value=expected_value,
        expected_unit=expected_unit,
        expected_currency=expected_currency,
    )


def _citation_bundle(
    run: dict[str, Any],
    payload: dict[str, Any],
    entity: str,
    metric_name: str,
    period: str,
    *,
    must_support: bool | None = None,
    expected_value: float | None = None,
    expected_unit: str = "",
    expected_currency: str = "",
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    support = True if must_support is None and metric_name not in RATIO_ALIASES else bool(must_support)
    if must_support is None and metric_name in RATIO_ALIASES:
        support = False
    found: list[str] = []
    tokens = list(_explicit_citation_tokens(payload))
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
    missing_input = False
    if metric_name in RATIO_ALIASES:
        if not inputs:
            missing_input = True
        for input_name, nested in inputs.items():
            if isinstance(nested, dict):
                tokens.extend(_explicit_citation_tokens(nested))
            nested_cites, _required = _citation_bundle(
                run,
                nested if isinstance(nested, dict) else {},
                entity,
                str(input_name),
                period,
                must_support=True,
                expected_value=input_value(nested) if isinstance(nested, dict) else None,
                expected_unit=input_unit(nested) if isinstance(nested, dict) else "",
                expected_currency=input_currency(nested) if isinstance(nested, dict) else "",
            )
            found.extend(nested_cites)
            if not nested_cites:
                missing_input = True
    for token in tokens:
        row = _evidence_row_for_token(run, token)
        if row is None:
            continue
        if str(row.get("entity") or "").lower() != entity.lower():
            continue
        item_period = str(row.get("period") or "")
        if period and item_period and item_period not in {"latest", "model", "unknown"} and not _periods_compatible(period, item_period):
            continue
        if support and not _evidence_supports_metric(
            row,
            metric_name,
            expected_value=expected_value,
            expected_unit=expected_unit or str(payload.get("unit") or ""),
            expected_currency=expected_currency or str(payload.get("currency") or ""),
        ):
            continue
        citation = str(row.get("citation") or token).strip()
        if citation:
            found.append(citation)
    unique = tuple(dict.fromkeys(found))
    required = unique + (("__missing_input_evidence__",) if missing_input else ())
    return unique, required


def _allowed_citations(fact: SupportedFact, evidence_rows: list[dict[str, Any]]) -> set[str]:
    del evidence_rows
    return {item.strip().lower() for item in fact.citations if item.strip()}


def _citation_matches_fact(token: str, allowed: set[str]) -> bool:
    needle = token.strip().lower()
    if not needle or not allowed:
        return False
    return needle in allowed


def _best_fact(matches: list[SupportedFact], period: str) -> SupportedFact:
    if period:
        dated_compatible = [
            fact
            for fact in matches
            if _period_has_year(fact.period) and _periods_compatible(period, fact.period)
        ]
        if dated_compatible:
            return dated_compatible[0]
        dated = [fact for fact in matches if _period_has_year(fact.period)]
        if dated:
            return dated[0]
    return matches[0]


def _period_has_year(label: str) -> bool:
    return bool(re.search(r"20\d{2}", label or ""))


_UNSPECIFIED_PERIODS = frozenset(
    {"", "latest", "unknown", "unspecified", "n/a", "na", "none", "model"}
)


def _period_is_unspecified(label: str) -> bool:
    token = re.sub(r"\s+", "", (label or "").strip().lower())
    return token in _UNSPECIFIED_PERIODS or not _period_has_year(label)


def _periods_compatible(left: str, right: str) -> bool:
    if _period_is_unspecified(left) and _period_is_unspecified(right):
        return True
    if _period_is_unspecified(left) or _period_is_unspecified(right):
        return False
    years_left = re.findall(r"20\d{2}", left)
    years_right = re.findall(r"20\d{2}", right)
    if years_left and years_right:
        return years_left[0] == years_right[0]
    return False


def _values_close(
    observed: float,
    fact: SupportedFact,
    *,
    percent: bool,
    unit_hint: str,
    observed_currency: str,
    observed_scale: float | None,
    case: dict[str, Any],
) -> bool:
    ratio_tol = float(case.get("numeric_tolerance", 0.001))
    pct_tol = float(case.get("visible_percent_tolerance", 0.05))
    fact_unit = (fact.unit or "").lower()
    ratio_fact = fact.metric in RATIO_ALIASES or fact_unit == "ratio"
    percent_fact = fact_unit in {"%", "percent", "pct"}
    if ratio_fact or percent_fact or percent:
        if percent_fact:
            expected_pct = float(fact.value)
            expected_ratio = expected_pct / 100.0
        else:
            expected_ratio = float(fact.value)
            expected_pct = expected_ratio * 100.0
        if percent:
            return math.isclose(observed, expected_pct, abs_tol=pct_tol, rel_tol=0.0)
        if ratio_fact or percent_fact:
            return math.isclose(observed, expected_ratio, abs_tol=ratio_tol, rel_tol=0.0)

    fact_currency = (fact.currency or "").upper()
    if observed_currency:
        observed_code = observed_currency.upper()
        if observed_code not in _KNOWN_ISO:
            return False
        if fact_currency and observed_code != fact_currency:
            return False
        if not fact_currency and observed_code not in {"USD", ""}:
            return False
    fact_scale = _scale_in(fact_unit) or 1.0
    vis_scale = observed_scale or _scale_in(unit_hint) or fact_scale
    expected_base = float(fact.value) * fact_scale
    observed_base = observed * vis_scale
    money_tol = max(abs(expected_base) * 0.01, 0.05 * vis_scale)
    return math.isclose(observed_base, expected_base, abs_tol=money_tol, rel_tol=0.0)


def _metric_value(facts: list[SupportedFact], entity: str, metric: str) -> float | None:
    for fact in facts:
        if fact.entity.lower() == entity.lower() and fact.metric == metric:
            return fact.value
    return None


def _finding(code: str, message: str, *, severity: str = "high", extra: dict[str, Any] | None = None) -> Finding:
    target = {"code": code}
    if extra:
        target.update(extra)
    return Finding(
        metric="visible_supported_claims",
        severity=severity,
        message=message,
        recommendation="Keep user-visible numeric/entity/period/unit claims aligned with verified metrics and evidence citations.",
        action="rewrite",
        target=target,
    )
