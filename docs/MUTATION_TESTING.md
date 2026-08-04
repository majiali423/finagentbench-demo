# Mutation Testing

Mutation testing verifies that the benchmark detects known-bad FinRuns. It is a
test of the evaluator, not a way to tune Agent output.

## Core reliability mutations

| Mutation | Expected detection |
|----------|--------------------|
| `wrong_number` | `numeric_correctness` |
| `wrong_entity` | `entity_coverage` |
| `missing_citation` | `evidence_coverage`, `evidence_consistency` |
| `missing_risk` | `risk_disclosure`, `section_presence` |

Report as **Core reliability mutations: 4/4**.

## Extended provenance/period mutations

| Mutation | Expected detection |
|----------|--------------------|
| `missing_metric_period_provenance` | `retrieval_provenance` |
| `query_period_source` | `retrieval_provenance` |
| `assumed_period_alignment` | `retrieval_provenance` |
| `missing_source_record` | `retrieval_provenance` |
| `formula_cross_period_inputs` | `retrieval_provenance` |
| `missing_period_alignment` | `retrieval_provenance` |
| `metric_period_drift` | `retrieval_provenance` |

Report separately as **Extended provenance/period mutations: 7/7**.
Do not fold these into the core 4/4 figure.

Definitions: `benchmarks/mutations/suite.json`.

## Run

```bash
python scripts/run_mutation_suite.py
```

Outputs:

- `outputs/mutation_detection_report.json`
- `outputs/mutation_detection_report.md`

Exit code is non-zero unless core and extended negative controls are detected
and clean baselines have no false positives.

## CI policy

The mutation suite runs on the Python 3.12 full CI lane. JSON/Markdown reports
are uploaded as workflow artifacts. Adding a metric does not permit lowering
existing thresholds or removing a mutation.

## Fixture integrity

The suite deep-copies source fixtures before mutation. Release/demo commands
must never rewrite benchmark fixtures.
