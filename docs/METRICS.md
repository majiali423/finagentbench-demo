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

## Financial correctness

- `numeric_correctness`: safely recomputes formulas from exported inputs.
- `unit_currency_consistency`: checks explicit unit/currency alignment.
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
