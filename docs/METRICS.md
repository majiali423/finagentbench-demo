# Reliability Metrics

FinAgentBench is deterministic-first. The CI profile excludes live semantic
judges.

## Entity reliability

- `entity_coverage`: required entities are present.
- `entity_leakage`: forbidden/unrequested entities are absent.

Generic cases derived from the run are workflow checks, not sufficient issuer
leakage proof. Release gates pair issuer and compare cases.

## Execution structure

- `step_presence`: required Agent stages executed.
- `section_presence`: required report headings/aliases exist.
- `visible_output_integrity`: deterministically checks only `final_output` for
  reasoning/prompt leakage, unfinished text, empty Markdown headings, and invalid
  comparison claims. Ignores fenced code and blockquotes by default; treats tables
  and lists as complete section bodies. Case contracts may supply
  `peer_section_aliases` and `entity_aliases`. Regex-guessed unknown peers are at
  most medium severity; `forbidden_entities` remain high blockers. Finding
  `target.code` / `target.confidence` carry structured codes such as
  `reasoning_leak` and `truncated_output`.
- `visible_supported_claims`: binds entity+metric numeric assertions, units,
  periods, comparative direction, and optional citations in `final_output` to
  verified FinRun metrics/claims/evidence. Scoring v3 opt-in. Unverifiable prose
  is not counted as verified.

## Financial correctness

- `numeric_correctness`: safely recomputes formulas from exported inputs.
- `unit_currency_consistency`: checks explicit unit/currency alignment only
  (no hardcoded magnitude ceilings).
- `input_value_plausibility`: optional Case-driven magnitude bounds via
  `input_value_bounds` (min/max + unit). Absent bounds → no amplitude check.
  Findings state case-bounds violations without asserting a definite root cause.
- `temporal_consistency`: checks metric/evidence periods and market as-of dates.

## Evidence and provenance

- `evidence_coverage`: cited evidence exists per expected entity.
- `evidence_consistency`: metric inputs appear in entity-aligned evidence.
- `retrieval_provenance`: source/provider metadata meets case policy.

## Risk and compliance

- `risk_disclosure`: required risk types and research/advice boundary.
- `compliance_language`: flags unsafe guarantee/recommendation wording.
- `input_safety`: checks guardrail metadata where enabled.

## Semantic audit (optional)

- `evidence_support`
- `risk_quality`
- `compliance_semantic`

These require a configured/static judge. They are not default deterministic CI
gates and do not replace numeric/entity checks.

## Empty-check policy

When `require_checkable_metrics` is enabled, required numeric, evidence,
unit/currency and temporal checks with zero checkable items return score `0`,
`passed=false`, and a diagnostic finding.

## Threshold governance

Cases own `min_score`, weights and severity blocks. Release changes must review
case hashes. This RC did not lower any threshold.

Scoring is explicitly versioned. Cases without `scoring_version` use scoring v1;
their enabled metrics and weights remain unchanged. Scoring v2 cases opt in with
`"scoring_version": "2"` and may enable `visible_output_integrity` at zero
weight while retaining high-severity blocking. Scoring v3 cases opt in with
`"scoring_version": "3"` and may enable `visible_supported_claims` in
`enabled_metrics`. That metric is not part of the default v1 metric set, so
historical diligence replay scores stay on the v1 contract. It binds
numeric/entity/period/unit/direction/citation assertions in `final_output` to
verified metrics/claims/evidence. Unsupported scoring versions are rejected
before evaluation.

`visible_supported_claims` does not treat unverifiable prose as verified. Ordinary
non-financial counts (specialist nodes, page numbers, table numbers) and heading
years are ignored. Opening `visible_output_integrity` is not sufficient to catch
false percentages in the report body.

## Execution path

Cases may set `execution_path`:

- `contract_replay`: frozen FinRun/state replay (historical v1 diligence).
- `retrieval_qa`: retrieval/rerank/generate harnesses such as LEDGER; not the
  product graph.
- `product_workflow`: query (+ documents) through the LumenFin graph to the
  user-visible report, then FinRun export.

